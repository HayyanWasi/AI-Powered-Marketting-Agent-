"""The input brief handed to every planning specialist.

Assembled once from the campaign's brand/event data plus the marketer's
free-text goal, then rendered into each specialist's prompt.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.models.audience import AudienceProfile
from src.models.brand_context import BrandContext
from src.modules.linkedin.scheduling.models import SchedulePlan
from src.modules.planning.models.campaign_plan import ResearchStatus


class PlanBrief(BaseModel):
    """Everything the panel knows about the campaign before it starts."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    user_goal: str = ""
    campaign_id: str = ""
    company_profile_id: str = ""
    brand_version: str = ""
    intake_hash: str = ""
    brand: BrandContext | None = None
    company_name: str = ""
    brand_tone: str = ""
    brand_guidelines: str = ""
    campaign_type: str = ""
    campaign_name: str = ""
    objective: str = ""
    value_proposition: str = ""
    cta_url: str = ""
    category: str = ""
    target_audience: str = ""
    audience_profile: AudienceProfile | None = None
    campaign_start: str = ""
    campaign_end: str = ""
    campaign_timezone: str = "UTC"
    schedule_plan: SchedulePlan | None = None
    curriculum_breakdown: str = ""
    outcome_deliverable: str = ""
    ticket_price: str = ""
    event_date: str = ""
    venue: str = ""
    registration_link: str = ""
    platforms: tuple[str, ...] = ()
    guests: tuple[str, ...] = ()
    research_context: dict | None = None
    research_status: ResearchStatus = ResearchStatus.NOT_REQUESTED
    research_status_reason: str = ""

    def has_usable_research(self) -> bool:
        """Return True only if research_context contains verified usable evidence."""
        if not self.research_context or not isinstance(self.research_context, dict):
            return False
        rc = self.research_context
        if rc.get("status") in ("degraded", "no_evidence") or "error" in rc:
            return False

        brief_data = rc.get("research_brief")
        if isinstance(brief_data, dict):
            for dim in ("market", "competitor", "audience", "content", "channel", "trend"):
                dim_data = brief_data.get(dim)
                if isinstance(dim_data, dict) and (dim_data.get("key_findings") or dim_data.get("evidence_items")):
                    return True

        graph_data = rc.get("evidence_graph")
        return bool(isinstance(graph_data, dict) and graph_data.get("nodes"))

    def get_research_status(self) -> tuple[ResearchStatus, str]:
        """Compute truthful research status and reason from research_context."""
        if not self.research_context or not isinstance(self.research_context, dict):
            return ResearchStatus.NOT_REQUESTED, ""

        rc = self.research_context
        if rc.get("status") == "degraded" or "error" in rc:
            err = rc.get("error") or rc.get("reason") or "Research pre-hook failed"
            return ResearchStatus.DEGRADED, str(err)

        if rc.get("status") == "no_evidence":
            return ResearchStatus.NO_EVIDENCE, "Web search executed but returned no usable evidence."

        if self.has_usable_research():
            return ResearchStatus.AVAILABLE, "Live research completed with usable evidence."

        return ResearchStatus.NO_EVIDENCE, "Web search executed but returned no usable evidence."

    def to_template_vars(self, research: str = "") -> dict[str, str]:
        """Flatten to the variables the prompt templates expect."""
        res_str = research
        if not res_str and self.research_context:
            rc = self.research_context
            if "error" in rc:
                res_str = f"RESEARCH FAILED: {rc['error']}. Proceed without live data."
            if "error" in rc or rc.get("status") == "degraded":
                err_msg = rc.get("error") or rc.get("reason") or "Research unavailable"
                res_str = f"RESEARCH FAILED: {err_msg}. Proceed without live data."
            elif rc.get("status") == "no_evidence":
                res_str = "NO WEB EVIDENCE FOUND: Search returned no results. Proceed based on internal knowledge."
            else:
                brief_data = rc.get("research_brief", {})
                findings = []
                if isinstance(brief_data, dict):
                    for dim in ("market", "competitor", "audience", "content", "channel", "trend"):
                        dim_data = brief_data.get(dim, {})
                        if isinstance(dim_data, dict):
                            kf = dim_data.get("key_findings", [])
                            if kf:
                                findings.append(f"[{dim.upper()}] " + "; ".join(kf[:3]))
                res_str = "\nWEB RESEARCH EVIDENCE:\n" + "\n".join(findings) if findings else ""
                if not res_str:
                    res_str = "NO WEB EVIDENCE FOUND: Search returned no results. Proceed based on internal knowledge."

        guests_val = (
            "\n".join(f"- FEATURED SPEAKER/GUEST: {g}" for g in self.guests)
            if self.guests
            else "(none)"
        )

        return {
            "brand_identity": self.brand.as_prompt() if self.brand else "(not specified)",
            "user_goal": self.user_goal or "(not specified)",
            "company_name": self.company_name or "(not specified)",
            "brand_tone": self.brand_tone or "(not specified)",
            "brand_guidelines": self.brand_guidelines or "(not specified)",
            # Compact guardrails line for the chief (avoids re-sending full
            # BrandContext prose): the negative guardrails, else the guidelines.
            "brand_guardrails": (
                "; ".join(self.brand.negative_guardrails)
                if self.brand and self.brand.negative_guardrails
                else (self.brand_guidelines or "(none specified)")
            ),
            "campaign_type": self.campaign_type or "(not specified)",
            "campaign_name": self.campaign_name or "(not specified)",
            "objective": self.objective or "(not specified)",
            "value_proposition": self.value_proposition or "(not specified)",
            "cta_url": self.cta_url or "(not specified)",
            "category": self.category or "(not specified)",
            "target_audience": self.target_audience or "(not specified)",
            "audience_profile": (
                self.audience_profile.model_dump_json() if self.audience_profile else "(not specified)"
            ),
            # Compact, immutable: line number (the planner's slot reference) +
            # local day/date/time + timezone. The UUID and UTC timestamp are
            # resolved in code (_resolve_calendar_slot_ids) and never sent.
            "fixed_schedule_slots": (
                "\n".join(
                    f"{i + 1}. {slot.local_date} ({slot.local_date.strftime('%A')}) "
                    f"{slot.local_time} {slot.timezone}"
                    for i, slot in enumerate(self.schedule_plan.slots)
                )
                if self.schedule_plan else "(not generated)"
            ),
            "curriculum_breakdown": self.curriculum_breakdown or "(not specified)",
            "outcome_deliverable": self.outcome_deliverable or "(not specified)",
            "ticket_price": self.ticket_price or "(not specified)",
            "event_date": self.event_date or "(not specified)",
            "venue": self.venue or "(not specified)",
            "registration_link": self.registration_link or "(not specified)",
            "platforms": ", ".join(self.platforms) or "(not specified)",
            "guests": guests_val,
            "research": f"\nWEB RESEARCH EVIDENCE:\n{res_str}" if res_str else "",
        }

    def as_prompt_vars(self, research: str = "") -> dict[str, str]:
        """Compatibility wrapper for existing planning callers."""
        return self.to_template_vars(research)

