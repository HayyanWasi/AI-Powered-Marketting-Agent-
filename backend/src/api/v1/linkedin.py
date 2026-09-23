"""FastAPI routes for LinkedIn Campaign Execution, Launchpad Preview, and Launch."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.modules.linkedin.generators.post_generator import LinkedInPostGenerator
from src.modules.linkedin.generators.sequence_generator import OutreachSequenceGenerator
from src.models.platform import PLATFORM_TEXT_LIMITS, Platform
from src.modules.linkedin.models import (
    AutoPilotConfig,
    PostStatus,
)
from src.gateways.unipile_gateway import get_unipile_gateway
from src.modules.planning.repositories.plan_repository import PlanNotFoundError
from src.modules.planning.services.plan_refinement_service import PlanRefinementService
from src.modules.research.models.research_brief import ResearchBrief
from src.repositories.base import BaseRepository
from src.services.campaign_context_service import (
    CampaignContextResolver,
    check_plan_freshness,
)
from src.services.campaign_service import CampaignService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/linkedin/campaigns", tags=["LinkedIn Campaign Launchpad"])


async def _require_campaign_owner(campaign_id: UUID, user: AuthenticatedUser) -> None:
    """Require the authenticated user to own the campaign before private access."""
    await CampaignService().get_campaign(campaign_id, UUID(user.id))


class GenerateContentRequest(BaseModel):
    research_brief_dict: dict[str, Any] | None = None


class PatchPostRequest(BaseModel):
    hook: str | None = None
    body: str | None = None
    cta_text: str | None = None
    scheduled_at: datetime | None = None
    timezone: str | None = None


class LaunchCampaignRequest(BaseModel):
    account_id: str
    config: AutoPilotConfig | None = None


class SchedulePostRequest(BaseModel):
    """Schedule/reschedule a single post at a future instant.

    ``scheduled_at`` must be timezone-aware; ``timezone`` is the IANA zone the UI
    displayed the time in (stored for round-tripping the local time back to the
    user). The publishing account is derived from the campaign's brand default —
    it is never supplied by the client here.
    """

    scheduled_at: datetime
    timezone: str


async def _resolve_generation_inputs(
    campaign_id: UUID, user: AuthenticatedUser
) -> tuple[Any, Any, ResearchBrief | None, dict[str, Any]]:
    """Resolve and validate everything required to generate LinkedIn content.

    Performs the same identity/staleness/calendar validation as the generate
    endpoints and returns ``(plan, inputs, brief, generator_kwargs)``. Raises the
    same HTTP 409s on invalid preconditions so both the batch and streaming
    endpoints reject before any generation begins.
    """
    inputs = await CampaignContextResolver().resolve(campaign_id, user.id)
    try:
        plan = await PlanRefinementService().get_plan(campaign_id)
    except PlanNotFoundError as exc:
        raise HTTPException(409, "Draft a campaign plan before generating LinkedIn content.") from exc
    if plan.campaign_id != campaign_id or not plan.channel_plan.calendar_slots:
        raise HTTPException(409, "The stored campaign plan has no valid content calendar. Refine it first.")

    # ── Verify Plan Identity / Staleness ──
    is_stale, _ = check_plan_freshness(plan, inputs)
    if is_stale:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign strategy is outdated because campaign or brand details changed. Regenerate the campaign strategy before generating content.",
        )

    intake = inputs.intake
    # Research comes from the persisted plan snapshot, not a replacement sent by the browser.
    brief = None
    research = plan.source_brief.get("research_context") or {}
    if research.get("research_brief"):
        brief = ResearchBrief.model_validate(research["research_brief"])
    has_guest = intake.get("has_guest") is True
    campaign_name_val = (
        intake.get("campaign_name")
        or intake.get("event_name")
        or getattr(inputs.campaign, "name", "")
        or ""
    )
    campaign_type_val = intake.get("campaign_type") or ""
    objective_val = intake.get("objective") or (inputs.campaign.goals.primary if inputs.campaign.goals else "") or ""
    value_prop_val = intake.get("value_proposition") or ""
    cta_url_val = intake.get("cta_url") or intake.get("registration_link") or ""

    generator_kwargs: dict[str, Any] = dict(
        event_name=intake.get("event_name") or "",
        event_date=intake.get("event_date") or "",
        venue=intake.get("venue") or "",
        registration_link=intake.get("registration_link") or "",
        target_audience=intake.get("target_audience") or "",
        curriculum_breakdown=intake.get("curriculum_breakdown") or "",
        ticket_price=intake.get("is_free_or_paid") or "",
        guest_name=intake.get("guest_name") if has_guest else None,
        guest_title=intake.get("guest_title") if has_guest else None,
        guest_profile=intake.get("guest_profile") if has_guest else None,
        timezone_name=inputs.campaign.schedule.timezone if inputs.campaign.schedule else "UTC",
        brand=inputs.brand,
        campaign_type=campaign_type_val,
        campaign_name=campaign_name_val,
        objective=objective_val,
        value_proposition=value_prop_val,
        cta_url=cta_url_val,
        campaign_category=intake.get("category") or "",
        outcome_value_proposition=value_prop_val or intake.get("outcome_deliverable") or "",
        product_facts=intake.get("product_facts") or intake.get("curriculum_breakdown") or "",
    )
    return plan, inputs, brief, generator_kwargs


def _persist_campaign_content(
    campaign_id: UUID, user_id: str, posts: list, outreach: Any
) -> list[dict[str, Any]]:
    """Atomically replace a campaign's LinkedIn posts and outreach sequence.

    This is the single canonical persistence step; it is unchanged from the batch
    flow and is only reached after every post and the outreach sequence have been
    generated successfully. Returns the saved (canonical, DB-identified) posts.
    """
    posts_payload = [p.to_dict() for p in posts]
    for p in posts_payload:
        p.pop("id", None)
        p.pop("campaign_id", None)
        p.pop("created_at", None)
    sequence_payload = outreach.model_dump(mode="json")
    sequence_payload.pop("id", None)
    sequence_payload.pop("campaign_id", None)
    sequence_payload.pop("created_at", None)

    repo = BaseRepository("linkedin_posts")
    try:
        res = repo.client.rpc(
            "replace_linkedin_campaign_content",
            {
                "p_campaign_id": str(campaign_id),
                "p_user_id": user_id,
                "p_posts": posts_payload,
                "p_sequence": sequence_payload,
            },
        ).execute()
    except Exception as exc:
        logger.exception("Atomic LinkedIn content persistence failed: %s", exc)
        raise HTTPException(503, "Could not save LinkedIn drafts. Please retry.") from exc

    return res.data.get("posts", []) if res.data else []


@router.post("/{campaign_id}/generate")
async def generate_campaign_content(
    campaign_id: UUID,
    req: GenerateContentRequest | None = None,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Generate research-grounded LinkedIn posts and outbound sequence for an approved campaign.

    Reads approved CampaignPlan and ResearchBrief from database/request.
    """
    plan, inputs, brief, generator_kwargs = await _resolve_generation_inputs(campaign_id, user)

    try:
        posts_task = LinkedInPostGenerator().generate_all_posts(
            campaign_id, plan, brief, **generator_kwargs
        )
        outreach_task = OutreachSequenceGenerator().generate_sequence(
            campaign_id, plan, brief, brand=inputs.brand
        )
        posts, outreach = await asyncio.gather(posts_task, outreach_task)
    except Exception as exc:
        logger.exception("LinkedIn post or outreach generation failed for campaign %s", campaign_id)
        raise HTTPException(502, "LinkedIn generation failed. Please retry.") from exc

    saved = _persist_campaign_content(campaign_id, user.id, posts, outreach)
    return {
        "status": "success",
        "posts_generated": len(saved),
        "sequence_generated": True,
        "posts": saved,
        "plan_version": plan.version,
        "company_profile_id": str(inputs.brand.company_profile_id),
    }


@router.post("/{campaign_id}/generate/stream")
async def generate_campaign_content_stream(
    campaign_id: UUID,
    req: GenerateContentRequest | None = None,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> StreamingResponse:
    """Progressive (post-by-post) variant of ``/generate``.

    Emits newline-delimited JSON progress events so the UI can reveal each
    completed post as soon as its full structured generation succeeds, without
    waiting for the whole campaign. Only fully validated posts are emitted, and
    canonical persistence remains atomic: nothing is saved until every post and
    the outreach sequence succeed, at which point one RPC replaces the content and
    ``generation_completed`` carries the canonical (DB-identified) posts. A failure
    at any point emits ``generation_failed`` and persists nothing.

    Generation concurrency, scheduling, provider order, and persistence semantics
    are identical to ``/generate`` — this endpoint only exposes progress.
    """
    # Validate preconditions BEFORE streaming so bad requests still get real HTTP
    # status codes (409/…) rather than a 200 stream carrying an error event.
    plan, inputs, brief, generator_kwargs = await _resolve_generation_inputs(campaign_id, user)
    total_posts = len(plan.channel_plan.calendar_slots)

    async def event_stream():
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        completed = 0

        async def on_post_started(index: int, slot_id: str, total: int) -> None:
            await queue.put(
                {
                    "event": "post_started",
                    "index": index,
                    "total_posts": total,
                    "slot_id": slot_id,
                }
            )

        async def on_post_completed(index: int, slot_id: str, total: int, post) -> None:
            nonlocal completed
            completed += 1
            payload = post.to_dict()
            # Strip DB/identity fields not yet assigned; this is a provisional
            # preview until generation_completed carries the canonical rows.
            payload.pop("id", None)
            payload.pop("campaign_id", None)
            payload.pop("created_at", None)
            await queue.put(
                {
                    "event": "post_completed",
                    "index": index,
                    "total_posts": total,
                    "slot_id": slot_id,
                    "post": payload,
                }
            )

        async def run() -> None:
            try:
                posts_task = LinkedInPostGenerator().generate_all_posts(
                    campaign_id,
                    plan,
                    brief,
                    on_post_started=on_post_started,
                    on_post_completed=on_post_completed,
                    **generator_kwargs,
                )
                outreach_task = OutreachSequenceGenerator().generate_sequence(
                    campaign_id, plan, brief, brand=inputs.brand
                )
                posts, outreach = await asyncio.gather(posts_task, outreach_task)
                saved = _persist_campaign_content(campaign_id, user.id, posts, outreach)
                await queue.put(
                    {
                        "event": "generation_completed",
                        "completed_count": len(saved),
                        "total_posts": total_posts,
                        "posts": saved,
                        "plan_version": plan.version,
                        "company_profile_id": str(inputs.brand.company_profile_id),
                    }
                )
            except Exception:
                logger.exception(
                    "Progressive LinkedIn generation failed for campaign %s", campaign_id
                )
                await queue.put(
                    {
                        "event": "generation_failed",
                        "error": "LinkedIn generation failed. Please retry.",
                        "completed_count": completed,
                        "total_posts": total_posts,
                    }
                )
            finally:
                await queue.put(None)

        yield json.dumps(
            {
                "event": "generation_started",
                "campaign_id": str(campaign_id),
                "total_posts": total_posts,
            }
        ) + "\n"

        worker = asyncio.create_task(run())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield json.dumps(item) + "\n"
        finally:
            await worker

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/{campaign_id}/preview")
async def get_launchpad_preview(
    campaign_id: UUID,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get an owned campaign's Launchpad preview data."""
    await _require_campaign_owner(campaign_id, user)
    posts_repo = BaseRepository("linkedin_posts")
    seq_repo = BaseRepository("outreach_sequences")

    posts: list = []
    sequence = None

    try:
        posts_res = (
            posts_repo.client.table(posts_repo.table_name)
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        posts = posts_res.data if posts_res.data else []
    except Exception as e:
        logger.warning("linkedin_posts table not ready: %s", e)

    try:
        seq_res = (
            seq_repo.client.table(seq_repo.table_name)
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        sequence = seq_res.data[0] if seq_res.data and len(seq_res.data) > 0 else None
    except Exception as e:
        logger.warning("outreach_sequences table not ready: %s", e)

    config = AutoPilotConfig().model_dump()

    return {
        "campaign_id": str(campaign_id),
        "posts": posts,
        "outreach_sequence": sequence,
        "autopilot_config": config,
    }


@router.patch("/{campaign_id}/posts/{post_id}")
async def patch_post(
    campaign_id: UUID,
    post_id: UUID,
    req: PatchPostRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Quick edit a post belonging to an owned campaign."""
    await _require_campaign_owner(campaign_id, user)
    posts_repo = BaseRepository("linkedin_posts")

    try:
        existing_res = (
            posts_repo.client.table(posts_repo.table_name)
            .select("*")
            .eq("id", str(post_id))
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"linkedin_posts table not available. Run migration first. ({e})",
        ) from e

    if not existing_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found in campaign {campaign_id}",
        )
    existing = existing_res.data[0]
    current_status = existing.get("status")

    # Status guards: published, publishing, scheduled are blocked from editing
    if current_status == PostStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot edit post: post is already published.",
        )
    if current_status == PostStatus.PUBLISHING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot edit post: post is currently publishing.",
        )
    if current_status == PostStatus.SCHEDULED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot edit post: post is scheduled. Reschedule or cancel schedule before editing content.",
        )

    update_data: dict[str, Any] = {}

    if req.hook is not None:
        update_data["hook"] = req.hook
    if req.body is not None:
        update_data["body"] = req.body
    if req.cta_text is not None:
        update_data["cta_text"] = req.cta_text
    if req.scheduled_at is not None:
        if req.scheduled_at.tzinfo is None:
            raise HTTPException(422, "scheduled_at must include a timezone offset.")
        update_data["scheduled_at"] = req.scheduled_at.isoformat()
    if req.timezone is not None:
        try:
            ZoneInfo(req.timezone)
        except Exception as exc:
            raise HTTPException(422, f"Invalid scheduling timezone: {req.timezone}") from exc
        update_data["timezone"] = req.timezone

    # If no updates were provided, return the existing row directly
    if not update_data:
        return existing

    # Recompute and validate full_content if hook, body, or cta_text were changed
    if "hook" in update_data or "body" in update_data or "cta_text" in update_data:
        hook = update_data.get("hook", existing.get("hook") or "")
        body = update_data.get("body", existing.get("body") or "")
        cta = update_data.get("cta_text", existing.get("cta_text") or "")
        full_content = f"{hook}\n\n{body}\n\n{cta}".strip()

        char_limit = PLATFORM_TEXT_LIMITS[Platform.LINKEDIN]
        char_count = len(full_content)
        if char_count > char_limit:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"LinkedIn post exceeds maximum length of {char_limit} characters (current: {char_count}).",
            )
        update_data["full_content"] = full_content

    try:
        res = (
            posts_repo.client.table(posts_repo.table_name)
            .update(update_data)
            .eq("id", str(post_id))
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post {post_id} not found",
            )
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"linkedin_posts table update failed: {e}",
        ) from e


def _validate_future_schedule(scheduled_at: datetime, timezone: str) -> None:
    """Reject naive, past, or bad-timezone schedule targets (HTTP 422)."""
    if scheduled_at.tzinfo is None:
        raise HTTPException(422, "scheduled_at must include a timezone offset.")
    try:
        ZoneInfo(timezone)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, f"Invalid scheduling timezone: {timezone}") from exc
    if scheduled_at <= datetime.now(UTC):
        raise HTTPException(422, "scheduled_at must be in the future.")


async def _resolve_brand_publishing_account(
    user_id: str, campaign: Any, action_verb: str = "scheduling"
) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve the LinkedIn account a campaign's brand publishes through.

    Returns ``(account_row, None)`` on success or ``(None, reason)`` where reason
    is a human message explaining why no account is usable. The account is taken
    from ``company_profiles.default_linkedin_account_id`` (Phase C brand binding),
    is re-checked to belong to ``user_id``, and must be ``connected``. Client
    input never influences which account is chosen.
    """
    company_profile_id = getattr(campaign, "company_profile_id", None)
    if not company_profile_id:
        return None, "This campaign is not linked to a brand, so no LinkedIn account can be resolved."

    profiles = BaseRepository("company_profiles")
    try:
        res = (
            profiles.client.table("company_profiles")
            .select("id,default_linkedin_account_id")
            .eq("id", str(company_profile_id))
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        prows = res.data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("company_profiles lookup failed during %s: %s", action_verb, e)
        return None, "Could not read the brand for this campaign."
    if not prows:
        return None, "Brand not found for this campaign."

    account_pk = prows[0].get("default_linkedin_account_id")
    if not account_pk:
        return None, (
            f"Choose a LinkedIn account for this brand before {action_verb}. "
            "Open the brand and connect or select a LinkedIn account."
        )

    accounts = BaseRepository("linkedin_accounts")
    try:
        ares = (
            accounts.client.table("linkedin_accounts")
            .select("*")
            .eq("id", str(account_pk))
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        arows = ares.data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("linkedin_accounts lookup failed during %s: %s", action_verb, e)
        return None, "Could not read the brand's LinkedIn account."
    if not arows:
        return None, "The brand's LinkedIn account is no longer available. Choose another account for this brand."
    if arows[0].get("status") != "connected":
        return None, f"The brand's LinkedIn account is disconnected. Reconnect it before {action_verb}."
    return arows[0], None


async def _load_owned_post(campaign_id: UUID, post_id: UUID) -> tuple[BaseRepository, dict[str, Any]]:
    """Fetch a post that belongs to the campaign, or raise 404/503."""
    posts_repo = BaseRepository("linkedin_posts")
    try:
        res = (
            posts_repo.client.table(posts_repo.table_name)
            .select("*")
            .eq("id", str(post_id))
            .eq("campaign_id", str(campaign_id))
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"linkedin_posts table not available. Run migration first. ({e})",
        ) from e
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found in campaign {campaign_id}",
        )
    return posts_repo, res.data[0]


@router.post("/{campaign_id}/posts/{post_id}/schedule")
async def schedule_post(
    campaign_id: UUID,
    post_id: UUID,
    req: SchedulePostRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Schedule a single DRAFT post for future auto-publish.

    The publishing account is derived from the campaign's brand default (never
    from the client). The draft -> scheduled transition is an atomic guarded
    update, so two concurrent schedule calls cannot both win. Does not publish and
    never contacts LinkedIn.
    """
    campaign = await CampaignService().get_campaign(campaign_id, UUID(user.id))
    _validate_future_schedule(req.scheduled_at, req.timezone)

    posts_repo, existing = await _load_owned_post(campaign_id, post_id)
    current_status = existing.get("status")
    if current_status != PostStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only draft posts can be scheduled (post is '{current_status}').",
        )

    # LinkedIn length guard on the content that would actually be published.
    full_content = existing.get("full_content") or ""
    char_limit = PLATFORM_TEXT_LIMITS[Platform.LINKEDIN]
    if len(full_content) > char_limit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"LinkedIn post exceeds maximum length of {char_limit} characters (current: {len(full_content)}).",
        )

    account, reason = await _resolve_brand_publishing_account(str(user.id), campaign)
    if account is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=reason)

    try:
        result = (
            posts_repo.client.table(posts_repo.table_name)
            .update(
                {
                    "status": PostStatus.SCHEDULED.value,
                    "scheduled_at": req.scheduled_at.isoformat(),
                    "timezone": req.timezone,
                    "linkedin_account_id": account["unipile_account_id"],
                }
            )
            .eq("id", str(post_id))
            .eq("campaign_id", str(campaign_id))
            .eq("status", PostStatus.DRAFT.value)  # atomic guard: exactly-one winner
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not schedule the post: {e}",
        ) from e
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Post is no longer a draft (it may have just been scheduled elsewhere).",
        )
    return result.data[0]


@router.post("/{campaign_id}/posts/{post_id}/reschedule")
async def reschedule_post(
    campaign_id: UUID,
    post_id: UUID,
    req: SchedulePostRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Move an already-SCHEDULED post to a new future time.

    Preserves the account binding and content. Guarded by ``status='scheduled'``
    so if the publisher has already claimed the post (``publishing``) the
    reschedule fails with 409 instead of clobbering an in-flight publish.
    """
    await _require_campaign_owner(campaign_id, user)
    _validate_future_schedule(req.scheduled_at, req.timezone)

    posts_repo, existing = await _load_owned_post(campaign_id, post_id)
    current_status = existing.get("status")
    if current_status != PostStatus.SCHEDULED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only scheduled posts can be rescheduled (post is '{current_status}').",
        )

    try:
        result = (
            posts_repo.client.table(posts_repo.table_name)
            .update(
                {
                    "scheduled_at": req.scheduled_at.isoformat(),
                    "timezone": req.timezone,
                }
            )
            .eq("id", str(post_id))
            .eq("campaign_id", str(campaign_id))
            .eq("status", PostStatus.SCHEDULED.value)  # lose the race -> no rows
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reschedule the post: {e}",
        ) from e
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Post is no longer scheduled — it may be publishing now. Reschedule is not possible.",
        )
    return result.data[0]


@router.post("/{campaign_id}/posts/{post_id}/cancel-schedule")
async def cancel_post_schedule(
    campaign_id: UUID,
    post_id: UUID,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Return a SCHEDULED post to DRAFT so it will not auto-publish.

    Clears ``scheduled_at`` and the post's account binding (the brand keeps its
    default; a later schedule rebinds from the brand). Guarded by
    ``status='scheduled'`` so a post the publisher already claimed
    (``publishing``/``published``) cannot be cancelled out from under it.
    """
    await _require_campaign_owner(campaign_id, user)

    posts_repo, existing = await _load_owned_post(campaign_id, post_id)
    current_status = existing.get("status")
    if current_status != PostStatus.SCHEDULED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only scheduled posts can be cancelled (post is '{current_status}').",
        )

    try:
        result = (
            posts_repo.client.table(posts_repo.table_name)
            .update(
                {
                    "status": PostStatus.DRAFT.value,
                    "scheduled_at": None,
                    "linkedin_account_id": None,
                }
            )
            .eq("id", str(post_id))
            .eq("campaign_id", str(campaign_id))
            .eq("status", PostStatus.SCHEDULED.value)  # lose the race -> no rows
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not cancel the schedule: {e}",
        ) from e
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Post is no longer scheduled — it may be publishing now. Cancel is not possible.",
        )
    return result.data[0]


async def _resolve_verified_account(user_id: str, unipile_account_id: str) -> dict[str, Any] | None:
    """Return the caller's verified LinkedIn account row, or ``None`` if invalid.

    The account must be (1) persisted in ``linkedin_accounts``, (2) owned by
    ``user_id``, and (3) currently ``connected``. As a best-effort freshness
    check the account is reverified live against Unipile; a definitive
    non-LinkedIn/absent result downgrades the stored status and rejects. A
    transient/ambiguous Unipile error falls back to the stored status (which the
    connect/refresh flow keeps current) rather than failing a valid launch.

    A client-supplied ``unipile_account_id`` is never trusted on its own — it is
    only ever accepted when it matches a row this user owns.
    """
    if not unipile_account_id:
        return None
    repo = BaseRepository("linkedin_accounts")
    try:
        res = (
            repo.client.table("linkedin_accounts")
            .select("*")
            .eq("user_id", user_id)
            .eq("unipile_account_id", unipile_account_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        logger.warning("linkedin_accounts lookup failed during launch: %s", e)
        return None
    if not rows:
        return None
    row = rows[0]
    if row.get("status") != "connected":
        return None

    # Best-effort live reverification (get_account swallows transient errors and
    # returns None, so only reject on a value that is clearly not LinkedIn).
    account = await get_unipile_gateway().get_account(unipile_account_id)
    if account is not None:
        provider = str(account.get("provider") or account.get("type") or "").upper()
        if "LINKEDIN" not in provider:
            try:
                repo.client.table("linkedin_accounts").update(
                    {"status": "disconnected", "updated_at": datetime.now(UTC).isoformat()}
                ).eq("id", row["id"]).execute()
            except Exception:  # noqa: BLE001 - status drift is best-effort
                pass
            return None
    return row


@router.post("/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: UUID,
    req: LaunchCampaignRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Activate Auto-Pilot for an owned campaign.

    The chosen LinkedIn account is verified to be one the caller owns and that is
    currently connected before any post is scheduled. Client-supplied account ids
    are never trusted directly; an invalid, unowned, or disconnected account
    rejects the launch and schedules nothing.
    """
    await _require_campaign_owner(campaign_id, user)

    account = await _resolve_verified_account(str(user.id), req.account_id)
    if account is None:
        raise HTTPException(
            409,
            "The selected LinkedIn account is not connected to your account. "
            "Connect a LinkedIn account in the Autopilot Control Room before launching.",
        )
    verified_account_id = account["unipile_account_id"]

    posts_repo = BaseRepository("linkedin_posts")

    try:
        result = posts_repo.client.table(posts_repo.table_name).update(
            {
                "status": PostStatus.SCHEDULED.value,
                "linkedin_account_id": verified_account_id,
            }
        ).eq("campaign_id", str(campaign_id)).eq("status", PostStatus.DRAFT.value).execute()
        if not result.data:
            raise HTTPException(409, "No draft LinkedIn posts are available to schedule.")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Could not bind and schedule LinkedIn posts: %s", e)
        raise HTTPException(
            409,
            "The LinkedIn schedule conflicts with an existing post or could not be activated.",
        ) from e

    return {
        "status": "active",
        "campaign_id": str(campaign_id),
        "account_id": verified_account_id,
        "message": "Campaign activated! Auto-Pilot worker will publish posts and execute outreach daily at 09:00 AM.",
    }


@router.get("/{campaign_id}/status")
async def get_campaign_execution_status(
    campaign_id: UUID,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get execution statistics for an owned campaign."""
    await _require_campaign_owner(campaign_id, user)
    posts_repo = BaseRepository("linkedin_posts")
    seq_repo = BaseRepository("outreach_sequences")

    posts: list = []
    sequences: list = []

    try:
        posts_res = (
            posts_repo.client.table(posts_repo.table_name)
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        posts = posts_res.data if posts_res.data else []
    except Exception as e:
        logger.warning("linkedin_posts table not ready: %s", e)

    try:
        seq_res = (
            seq_repo.client.table(seq_repo.table_name)
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        sequences = seq_res.data if seq_res.data else []
    except Exception as e:
        logger.warning("outreach_sequences table not ready: %s", e)

    published_count = sum(1 for p in posts if p.get("status") == "published")
    scheduled_count = sum(1 for p in posts if p.get("status") == "scheduled")

    return {
        "campaign_id": str(campaign_id),
        "total_posts": len(posts),
        "posts_published": published_count,
        "posts_scheduled": scheduled_count,
        "total_outreach_leads": len(sequences),
        "connected_leads": sum(1 for s in sequences if s.get("status") in ("connected", "replied")),
        "replied_leads": sum(1 for s in sequences if s.get("status") == "replied"),
    }
