"""Outreach Sequence Generator — Generates research-grounded outbound messaging sequence."""

from __future__ import annotations

import logging
from uuid import UUID

from src.modules.linkedin.models import OutreachTemplate
from src.modules.planning.models.campaign_plan import CampaignPlan
from src.modules.research.models.research_brief import ResearchBrief
from src.modules.research.services.llm_router import LLMRouterService

logger = logging.getLogger(__name__)


class OutreachSequenceGenerator:
    """Generates 4-step outbound LinkedIn sequence anchored in research brief."""

    def __init__(self, llm_router: LLMRouterService | None = None) -> None:
        self.llm = llm_router or LLMRouterService()

    async def generate_sequence(
        self,
        campaign_id: UUID,
        plan: CampaignPlan,
        brief: ResearchBrief | None = None,
    ) -> OutreachTemplate:
        """Generate a 4-step outbound sequence template."""
        usp = plan.core_strategy.unique_selling_proposition if plan.core_strategy else ""
        diff = plan.competitive.differentiation_angle if plan.competitive else ""

        # Extract pain points from audience research
        pain_points = []
        if brief and brief.audience:
            pain_points = [e.claim for e in brief.audience.evidence_items[:3]]

        system_prompt = (
            "You are a B2B Outreach Specialist. Write a high-converting, non-spammy 4-step "
            "LinkedIn messaging sequence using exact audience pain points and differentiators."
        )

        user_prompt = f"""
Campaign Objective: {plan.title}
USP: {usp}
Differentiation: {diff}
Target Audience Pain Points (from research):
{chr(10).join(f"- {p}" for p in pain_points) if pain_points else "- Looking for efficient solutions"}

Generate 3 copy templates:
1. Connection Request Note (max 200 characters, subtle hook, NO hard pitch)
2. Value Message (sent after connection accepted: share insights, host seminar/guide, zero sales pressure)
3. Follow-up Message (sent 3 days later if no reply: short check-in)

Return ONLY valid JSON matching this schema:
{{
  "step_invite_msg": "Hi [First Name], saw your work in...",
  "step_value_msg": "Hi [First Name], thought you might find this useful...",
  "step_followup_msg": "Hi [First Name], just following up..."
}}
"""
        try:
            res = await self.llm.generate_json(system_prompt, user_prompt)
            return OutreachTemplate(
                campaign_id=campaign_id,
                step_invite_msg=res.get("step_invite_msg", "").strip(),
                step_value_msg=res.get("step_value_msg", "").strip(),
                step_followup_msg=res.get("step_followup_msg", "").strip(),
            )
        except Exception as e:
            logger.error("Failed to generate outreach sequence for campaign %s: %s", campaign_id, e)
            return OutreachTemplate(
                campaign_id=campaign_id,
                step_invite_msg="Hi [Name], loved your work. Would love to connect!",
                step_value_msg="Hi [Name], sharing a quick resource on our recent research.",
                step_followup_msg="Hi [Name], just checking if you had a chance to look at this.",
            )
