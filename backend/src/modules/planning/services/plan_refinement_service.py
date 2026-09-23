"""Plan refinement service — drives the planning graphs and persists their output.

Responsibilities:
- ``draft_plan``: runs the panel fan-out graph and stores v1 in Postgres.
- ``refine_plan``: loads the current plan + brief, runs the refinement graph,
  stores a new version and both conversation turns.
- ``approve_plan``: marks the plan approved so the generation gate passes.

All public methods are ``async`` because they hit the database and run async
LangGraph graphs. They are called from the plans API route.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from src.modules.linkedin.scheduling import ScheduleOptimizer
from src.modules.linkedin.scheduling.slot_validation import (
    ScheduleSlotMismatchError,
    normalize_calendar_slots,
)
from src.modules.linkedin.scheduling.timezone_resolver import resolve_scheduling_timezone
from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import (
    CampaignPlan,
    PlanMessage,
    PlanStatus,
    PlanVersion,
    ResearchStatus,
)
from src.modules.planning.repositories.plan_repository import (
    PlanNotFoundError,
    PlanRepository,
)
from src.modules.research.research_service import ResearchEngineService
from src.modules.workflow_engine.graphs import campaign_plan as plan_graph
from src.modules.workflow_engine.graphs import plan_refinement as refinement_graph

logger = logging.getLogger(__name__)


class PlanDraftError(Exception):
    """Raised when the panel graph fails to produce any plan."""


class PlanRefinementService:
    """Orchestrates plan drafting, refinement, and approval.

    One instance per request is fine — the repository constructs its
    Supabase client lazily.
    """

    def __init__(self, repository: PlanRepository | None = None) -> None:
        self._repo = repository or PlanRepository()

    # ── Public API ────────────────────────────────────────────────────────

    async def draft_plan(
        self,
        campaign_id: UUID,
        created_by: UUID,
        brief: PlanBrief,
        language: str = "en",
        tier: str = "Quick",
    ) -> CampaignPlan:
        """Run the research engine pre-hook, then run the 5-specialist panel and persist v1.

        Args:
            campaign_id: Campaign this plan belongs to.
            created_by: User triggering the draft.
            brief: Everything the panel knows before it starts.
            language: ISO language tag detected from the marketer's goal.
            tier: Research depth tier ("Quick", "Standard", "Deep").

        Returns:
            The freshly drafted CampaignPlan (version 1 or higher).

        Raises:
            PlanDraftError: If the graph produces no plan at all.
        """
        # Ensure the plan row exists.
        plan_row = await self._repo.get_or_create_plan_row(campaign_id, created_by, language)
        plan_id = UUID(plan_row["id"])

        # Build the neutral timing skeleton before any LLM runs. It remains
        # in memory until the completed plan version is persisted.
        today = datetime.now(UTC).date()
        start = date.fromisoformat(brief.campaign_start) if brief.campaign_start else today
        end = date.fromisoformat(brief.campaign_end) if brief.campaign_end else start + timedelta(days=29)
        resolved_timezone = resolve_scheduling_timezone(
            audience=brief.audience_profile,
            campaign_timezone=brief.campaign_timezone,
        )
        schedule_plan = ScheduleOptimizer.build(
            campaign_start=start,
            campaign_end=end,
            timezone_name=resolved_timezone.name,
            timezone_source=resolved_timezone.source,
            timezone_confidence=resolved_timezone.confidence,
            audience=brief.audience_profile,
            campaign_type=brief.campaign_type,
            objective=brief.objective,
            event_date=brief.event_date,
        )
        brief = brief.model_copy(update={"schedule_plan": schedule_plan})

        # Execute Autonomous Research Engine pre-hook to gather live web evidence
        research_context = None
        research_status = ResearchStatus.NOT_REQUESTED
        research_reason = ""
        if tier != "Quick":
            research_context = await self._run_research(brief, campaign_id, tier)
            if research_context:
                brief = brief.model_copy(update={"research_context": research_context})
                research_status, research_reason = brief.get_research_status()
        else:
            research_status = ResearchStatus.NOT_REQUESTED
            research_reason = "Research was not requested for Quick tier."
            if brief.research_context:
                research_status, research_reason = brief.get_research_status()

        # Warm the planning Ollama GPUs before the heavy specialist calls so a
        # cold first request does not miss the tunnel window and fall back to a
        # remote provider. Idempotent (warms once per process) and never raises
        # — a warm-up failure just leaves the remote fallback path in place.
        from src.modules.planning import warmup

        await warmup.ensure_planning_endpoints_warm()

        # Run the panel graph with enriched brief.
        graph = plan_graph.compile_graph(tier=tier)
        state = plan_graph.initial_state(brief)
        try:
            final_state = await graph.ainvoke(state)
        except Exception as exc:
            raise PlanDraftError("Planning failed. Please retry.") from exc

        plan: CampaignPlan | None = final_state.get("plan")
        if plan is None:
            raise PlanDraftError(
                f"Panel graph produced no plan for campaign {campaign_id}. "
                f"Failures: {final_state.get('failures', [])}"
            )

        # All 5 specialist sections are required — a specialist that failed
        # upstream (provider retry/failover exhausted) degrades to an empty
        # section rather than crashing the graph, but that is not a plan we
        # may save. Fail truthfully here, before any persistence, instead of
        # silently continuing with a partial plan. Full failure detail stays
        # server-side; the frontend gets a safe, non-leaking message.
        failures = final_state.get("failures", [])
        if failures:
            logger.error(
                "Specialist panel failed for campaign %s (%s); refusing to save a partial plan.",
                campaign_id,
                "; ".join(failures),
            )
            failed_names = sorted({f.split(":", 1)[0].strip() for f in failures})
            if failed_names == ["channel_plan"]:
                raise PlanDraftError("Channel planning failed. Please retry planning.")
            raise PlanDraftError(
                f"Planning failed: {', '.join(failed_names)} could not be generated. "
                "Please retry planning."
            )

        # No specialist failure was recorded, but the channel calendar is still
        # empty — same truthful failure, since there is nothing to validate.
        if not plan.channel_plan.calendar_slots:
            logger.error(
                "Channel plan for campaign %s produced no calendar slots despite no "
                "recorded specialist failure; refusing to save a partial plan.",
                campaign_id,
            )
            raise PlanDraftError("Channel planning failed. Please retry planning.")

        try:
            normalized_calendar = normalize_calendar_slots(
                plan.channel_plan.calendar_slots, schedule_plan
            )
        except ScheduleSlotMismatchError as exc:
            raise PlanDraftError(
                "Channel planner changed the fixed schedule slots. Please retry planning."
            ) from exc
        plan = plan.model_copy(update={
            "channel_plan": plan.channel_plan.model_copy(
                update={"calendar_slots": normalized_calendar}
            )
            })

        previous = await self._repo.get_latest_version(plan_id)
        next_version = previous.version + 1 if previous else 1

        # Stamp the plan with its identity, source snapshot and next version.
        from src.modules.planning.models.campaign_plan import InputIdentity
        input_id = InputIdentity(
            campaign_id=UUID(brief.campaign_id) if brief.campaign_id else campaign_id,
            company_profile_id=UUID(brief.company_profile_id) if brief.company_profile_id else None,
            brand_version=brief.brand_version,
            intake_hash=brief.intake_hash,
            user_goal=brief.user_goal,
            generated_at=datetime.utcnow().isoformat(),
        )

        plan = plan.model_copy(
            update={
                "campaign_id": campaign_id,
                "version": next_version,
                "plan_id": plan_id,
                "source_brief": brief.model_dump(mode="json"),
                "input_identity": input_id,
                "language": language,
                "status": PlanStatus.DRAFT,
                "research_status": research_status,
                "research_status_reason": research_reason,
                "schedule_plan": schedule_plan,
            }
        )

        await self._repo.add_version(
            plan_id,
            plan,
            change_summary="Initial draft by the specialist panel with web research ground truth.",
            sections_changed=("core_strategy", "channel_plan", "measurement", "competitive"),
            parent_version=previous.version if previous else None,
        )
        logger.info(
            "Plan v1 drafted for campaign %s (Research Enriched: %s)",
            "Plan v1 drafted for campaign %s (Research Status: %s, Enriched: %s)",
            campaign_id,
            research_status.value,
            bool(research_context),
        )
        return plan

    async def _run_research(self, brief: PlanBrief, campaign_id: UUID, tier: str) -> dict | None:
        """Run standalone Autonomous Research Engine pre-hook with fallback gracefully on error/timeout."""
        goal = brief.user_goal or brief.objective or brief.campaign_name or "Marketing Campaign"
        try:
            svc = ResearchEngineService()
            results = await asyncio.wait_for(
                svc.draft_research(
                    user_goal=goal,
                    company_name=brief.company_name,
                    tier=tier,
                    campaign_id=campaign_id,
                    campaign_type=brief.campaign_type,
                    audience=brief.target_audience,
                    category=brief.category,
                ),
                timeout=120.0,
            )
            if not isinstance(results, dict):
                return {"status": "no_evidence", "reason": "Research returned empty result."}

            brief_dict = results.get("research_brief")
            has_evidence = False
            if isinstance(brief_dict, dict):
                for dim in ("market", "competitor", "audience", "content", "channel", "trend"):
                    d = brief_dict.get(dim)
                    if isinstance(d, dict) and (d.get("key_findings") or d.get("evidence_items")):
                        has_evidence = True
                        break
            graph_dict = results.get("evidence_graph")
            if isinstance(graph_dict, dict) and graph_dict.get("nodes"):
                has_evidence = True

            if has_evidence:
                results["status"] = "available"
            else:
                results["status"] = "no_evidence"
                results["reason"] = "Web search completed but found no usable evidence."
            return results
        except Exception as e:
            logger.warning(
                "Pre-research hook failed or timed out (%s); continuing without web research", e
            )
            return {"error": str(e), "status": "degraded"}
            return {"error": str(e), "status": "degraded", "reason": f"Live research failed or timed out ({e})"}

    async def refine_plan(
        self,
        campaign_id: UUID,
        critique: str,
        user_id: UUID,
        brief: PlanBrief,
    ) -> tuple[CampaignPlan, str]:
        """Run one refinement turn and persist the result.

        Args:
            campaign_id: Campaign whose plan to refine.
            critique: The marketer's message.
            user_id: The user submitting the critique.
            brief: The original brief (unchanged — only the plan evolves).

        Returns:
            (revised_plan, reply) — the updated plan and the agent's reply.

        Raises:
            PlanNotFoundError: If no plan exists for this campaign.
            PlanDraftError: If the refinement graph cannot load state.
        """
        plan_row, current_plan = await self._load_current(campaign_id)
        plan_id = UUID(plan_row["id"])

        # Store the user's message before running so it appears in order.
        user_msg = PlanMessage(
            plan_id=plan_id,
            role="user",
            content=critique,
            language=current_plan.language,
        )
        await self._repo.add_message(user_msg)

        # Run the refinement graph.
        graph = refinement_graph.compile_graph()
        state = refinement_graph.initial_state(current_plan, brief, critique)
        try:
            final_state = await graph.ainvoke(state)
        except Exception as exc:
            raise PlanDraftError("Planning failed. Please retry.") from exc

        revised: CampaignPlan = final_state.get("revised_plan", current_plan)
        if "channel_plan" in final_state.get("sections_changed", ()):
            if current_plan.schedule_plan is None:
                raise PlanDraftError("Plan refinement cannot change fixed schedule slots.")
            try:
                normalized_calendar = normalize_calendar_slots(
                    revised.channel_plan.calendar_slots, current_plan.schedule_plan
                )
            except ScheduleSlotMismatchError as exc:
                raise PlanDraftError(
                    "Plan refinement cannot change fixed schedule slots."
                ) from exc
            revised = revised.model_copy(update={
                "channel_plan": revised.channel_plan.model_copy(
                    update={"calendar_slots": normalized_calendar}
                )
            })
        from src.modules.planning.models.campaign_plan import InputIdentity
        input_id = InputIdentity(
            campaign_id=UUID(brief.campaign_id) if brief.campaign_id else campaign_id,
            company_profile_id=UUID(brief.company_profile_id) if brief.company_profile_id else None,
            brand_version=brief.brand_version,
            intake_hash=brief.intake_hash,
            user_goal=brief.user_goal,
            generated_at=datetime.utcnow().isoformat(),
        )
        revised = revised.model_copy(
            update={
                "source_brief": brief.model_dump(mode="json"),
                "input_identity": input_id,
                "research_status": current_plan.research_status,
                "research_status_reason": current_plan.research_status_reason,
                "schedule_plan": current_plan.schedule_plan,
            }
        )
        reply: str = final_state.get("reply", "")
        sections_changed: tuple[str, ...] = final_state.get("sections_changed", ())
        language: str = final_state.get("language") or current_plan.language

        # Persist the new version only if something actually changed.
        new_version = current_plan.version
        if sections_changed:
            await self._repo.add_version(
                plan_id,
                revised,
                change_summary=critique[:200],
                sections_changed=sections_changed,
                parent_version=current_plan.version,
            )
            new_version = revised.version
            logger.info(
                "Plan v%d saved for campaign %s (changed: %s)",
                new_version,
                campaign_id,
                ", ".join(sections_changed),
            )

        # Store the assistant's reply.
        assistant_msg = PlanMessage(
            plan_id=plan_id,
            role="assistant",
            content=reply,
            language=language,
            sections_targeted=sections_changed,
            resulting_version=new_version if sections_changed else None,
        )
        await self._repo.add_message(assistant_msg)

        return revised, reply

    async def approve_plan(self, campaign_id: UUID, approved_by: UUID) -> CampaignPlan:
        """Mark a plan as approved.

        The approval is stored on the plan row (``approved_at``,
        ``approved_by``, ``status``). The current plan document is also
        patched with ``approved=True`` and a new version is appended so the
        version ledger reflects the approval moment.

        Args:
            campaign_id: Campaign whose plan to approve.
            approved_by: User approving the plan.

        Returns:
            The approved CampaignPlan.

        Raises:
            PlanNotFoundError: If no plan exists for this campaign.
        """
        plan_row, current_plan = await self._load_current(campaign_id)
        plan_id = UUID(plan_row["id"])

        approved_plan = current_plan.model_copy(
            update={
                "approved": True,
                "status": PlanStatus.APPROVED,
                "version": current_plan.version + 1,
            }
        )

        await self._repo.add_version(
            plan_id,
            approved_plan,
            change_summary="Plan approved by marketer.",
            sections_changed=(),
            parent_version=current_plan.version,
        )
        await self._repo.update_plan_row(
            plan_id,
            status=PlanStatus.APPROVED.value,
            approved_at=datetime.now(UTC).isoformat(),
            approved_by=str(approved_by),
        )
        logger.info("Plan approved for campaign %s", campaign_id)
        return approved_plan

    async def get_plan(self, campaign_id: UUID) -> CampaignPlan:
        """Return the current plan for a campaign.

        Raises:
            PlanNotFoundError: If no plan exists.
        """
        _, plan = await self._load_current(campaign_id)
        return plan

    async def get_messages(self, campaign_id: UUID) -> list[PlanMessage]:
        """Return the refinement conversation thread."""
        plan_row = await self._repo.get_plan_row(campaign_id)
        if not plan_row:
            raise PlanNotFoundError(f"No plan for campaign {campaign_id}")
        return await self._repo.list_messages(UUID(plan_row["id"]))

    async def list_versions(self, campaign_id: UUID) -> list[PlanVersion]:
        """Return all versions of the plan, newest first."""
        plan_row = await self._repo.get_plan_row(campaign_id)
        if not plan_row:
            raise PlanNotFoundError(f"No plan for campaign {campaign_id}")
        return await self._repo.list_versions(UUID(plan_row["id"]))

    async def get_version(self, campaign_id: UUID, version: int) -> PlanVersion | None:
        """Return a specific version of the plan."""
        plan_row = await self._repo.get_plan_row(campaign_id)
        if not plan_row:
            raise PlanNotFoundError(f"No plan for campaign {campaign_id}")
        return await self._repo.get_version(UUID(plan_row["id"]), version)

    # ── Private helpers ───────────────────────────────────────────────────

    async def _load_current(self, campaign_id: UUID) -> tuple[dict, CampaignPlan]:
        """Load the plan row and rebuild the current CampaignPlan from its latest version.

        Raises:
            PlanNotFoundError: If no plan row or no version exists yet.
        """
        plan_row = await self._repo.get_plan_row(campaign_id)
        if not plan_row:
            raise PlanNotFoundError(f"No plan found for campaign {campaign_id}")

        latest = await self._repo.get_latest_version(UUID(plan_row["id"]))
        if not latest:
            raise PlanNotFoundError(
                f"Plan exists for campaign {campaign_id} but has no versions yet"
            )

        plan = CampaignPlan.from_document(latest.document)
        return plan_row, plan
