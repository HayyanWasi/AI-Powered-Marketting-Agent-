"""The input brief handed to every planning specialist.

Assembled once from the campaign's brand/event data plus the marketer's
free-text goal, then rendered into each specialist's prompt.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PlanBrief(BaseModel):
    """Everything the panel knows about the campaign before it starts."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    user_goal: str = ""
    company_name: str = ""
    brand_tone: str = ""
    brand_guidelines: str = ""
    event_name: str = ""
    category: str = ""
    target_audience: str = ""
    curriculum_breakdown: str = ""
    outcome_deliverable: str = ""
    ticket_price: str = "Free"
    event_date: str = ""
    venue: str = ""
    registration_link: str = ""
    platforms: tuple[str, ...] = ()
    guests: tuple[str, ...] = ()
    research_context: dict | None = None

    def as_prompt_vars(self, research: str = "") -> dict[str, str]:
        """Flatten to the variables the prompt templates expect."""
        res_str = research
        if not res_str and self.research_context:
            rc = self.research_context
            brief_data = rc.get("research_brief", {})
            findings = []
            for dim in ("market", "competitor", "audience", "content", "channel", "trend"):
                dim_data = brief_data.get(dim, {})
                kf = dim_data.get("key_findings", [])
                if kf:
                    findings.append(f"[{dim.upper()}] " + "; ".join(kf[:3]))
            res_str = "\n".join(findings)

        guests_val = (
            "\n".join(f"- FEATURED SPEAKER/GUEST: {g}" for g in self.guests)
            if self.guests
            else "(none)"
        )

        return {
            "user_goal": self.user_goal or "(not specified)",
            "company_name": self.company_name or "(not specified)",
            "brand_tone": self.brand_tone or "(not specified)",
            "brand_guidelines": self.brand_guidelines or "(not specified)",
            "event_name": self.event_name or "(not specified)",
            "category": self.category or "(not specified)",
            "target_audience": self.target_audience or "(not specified)",
            "curriculum_breakdown": self.curriculum_breakdown or "(not specified)",
            "outcome_deliverable": self.outcome_deliverable or "(not specified)",
            "ticket_price": self.ticket_price or "Free",
            "event_date": self.event_date or "(not specified)",
            "venue": self.venue or "(not specified)",
            "registration_link": self.registration_link or "(not specified)",
            "platforms": ", ".join(self.platforms) or "(not specified)",
            "guests": guests_val,
            "research": f"\nWEB RESEARCH EVIDENCE:\n{res_str}" if res_str else "",
        }


    @classmethod
    def from_context(cls, context) -> PlanBrief:
        """Build a brief from a GenerationContext."""
        return cls(
            user_goal=context.user_goal,
            company_name=context.brand.company_name,
            brand_tone=context.brand.brand_tone,
            brand_guidelines=context.brand.brand_guidelines,
            event_name=context.event.event_name,
            event_date=context.event.event_date,
            venue=context.event.venue,
            registration_link=context.event.registration_link,
            platforms=context.event.platforms,
            guests=tuple(
                f"{g.full_name} — {g.position} at {g.organization}".strip(" —")
                for g in context.guests
            ),
        )
