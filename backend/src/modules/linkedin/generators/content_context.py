"""ContentContext builder — Extracts web-verified evidence from ResearchBrief for LLM post generation."""

from __future__ import annotations

import logging

from src.modules.linkedin.models import ContentContext, ResearchedFact
from src.modules.planning.models.campaign_plan import CalendarSlot, CampaignPlan
from src.modules.research.models.research_brief import ResearchBrief

logger = logging.getLogger(__name__)


class ContentContextBuilder:
    """Extracts research evidence and plan decisions to build ContentContext."""

    @staticmethod
    def build_context(
        slot: CalendarSlot,
        plan: CampaignPlan,
        brief: ResearchBrief | None = None,
        min_confidence: float = 3.5,
        # Intake/event data — passed through from intake_checklists
        event_name: str = "",
        event_date: str = "",
        venue: str = "",
        registration_link: str = "",
        target_audience: str = "",
        curriculum_breakdown: str = "",
        ticket_price: str = "Free",
        guest_name: str | None = None,
        guest_position: str | None = None,
        guest_organization: str | None = None,
        guest_profile: dict | None = None,
        post_time_str: str = "10:00 AM",
    ) -> ContentContext:
        """Construct a ContentContext for a specific CalendarSlot.

        Args:
            slot: The specific CalendarSlot to generate copy for.
            plan: The approved CampaignPlan.
            brief: The master ResearchBrief containing web-verified evidence items.
            min_confidence: Minimum composite confidence score to include an evidence item.
            event_name: Event name from intake_checklists.
            event_date: Event date from intake_checklists.
            venue: Event venue from intake_checklists.
            registration_link: Registration URL from intake_checklists.
            target_audience: Target audience from intake_checklists.
            curriculum_breakdown: Curriculum/content breakdown from intake_checklists.
            ticket_price: Pricing info from intake_checklists.
            guest_name: Guest speaker name from intake_checklists.
            guest_position: Guest speaker title from intake_checklists.
            guest_organization: Guest speaker organization.

        Returns:
            ContentContext populated with slot info, web-verified ResearchedFacts, and event data.
        """
        facts: list[ResearchedFact] = []

        if brief is not None:
            # Collect evidence items from all 6 dimensions
            dimensions = (
                brief.market,
                brief.competitor,
                brief.audience,
                brief.content,
                brief.channel,
                brief.trend,
            )

            for dim_summary in dimensions:
                for item in dim_summary.evidence_items:
                    conf_score = item.confidence.composite_score
                    if conf_score >= min_confidence:
                        # Match relevance to pillar or theme if possible, or include high-value claims
                        facts.append(
                            ResearchedFact(
                                fact_id=item.evidence_id,
                                dimension=item.dimension,
                                claim=item.claim,
                                quote=item.quote,
                                source_url=item.source.url if item.source else "",
                                confidence_score=conf_score,
                            )
                        )

        # Extract strategic anchors from plan
        differentiation = plan.competitive.differentiation_angle if plan.competitive else ""
        usp = plan.core_strategy.unique_selling_proposition if plan.core_strategy else ""
        tone = (
            plan.core_strategy.tone_of_voice if plan.core_strategy else "Professional & Data-driven"
        )

        return ContentContext(
            slot_id=slot.slot_id,
            slot_date=slot.date,
            scheduled_time=post_time_str,
            theme=slot.theme,
            messaging_pillar=slot.messaging_pillar,
            cta=slot.cta,
            phase=slot.phase.value if hasattr(slot.phase, "value") else str(slot.phase),
            format_type=slot.format_type or "Text Post",
            tone_of_voice=tone,
            researched_facts=tuple(facts),
            differentiation_angle=differentiation,
            usp=usp,
            guest_name=guest_name,
            guest_position=guest_position,
            guest_organization=guest_organization,
            event_name=event_name,
            event_date=event_date,
            venue=venue,
            registration_link=registration_link,
            target_audience=target_audience,
            curriculum_breakdown=curriculum_breakdown,
            ticket_price=ticket_price,
            guest_profile=guest_profile,
        )
