"""Outreach Sequence Generator — Generates research-grounded outbound messaging sequence."""

from __future__ import annotations

import logging
from uuid import UUID

from src.models.brand_context import BrandContext
from src.modules.linkedin.generators.local_llm_gate import (
    LINKEDIN_LOCAL_OLLAMA_TIMEOUT_SECONDS,
    linkedin_local_ollama_slot,
)
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
        brand: BrandContext | None = None,
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

        if brand is None:
            raise ValueError("Brand context is required for outreach generation.")
        user_prompt = f"""
BRAND IDENTITY AND REQUIRED COMMUNICATION RULES:
{brand.as_prompt()}
Follow the brand tone and guardrails. Do not invent brand facts.

Campaign Objective: {plan.title}
USP: {usp}
Differentiation: {diff}
Target Audience Pain Points (from research):
{chr(10).join(f"- {p}" for p in pain_points) if pain_points else "(not provided)"}

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
            # Share the LinkedIn local-Ollama gate with post generation so
            # outreach never runs against the single GPU alongside a post.
            async with linkedin_local_ollama_slot(self.llm):
                res = await self.llm.generate_json(
                    system_prompt,
                    user_prompt,
                    timeout=LINKEDIN_LOCAL_OLLAMA_TIMEOUT_SECONDS,
                )
            if not all(isinstance(res.get(k), str) and res[k].strip() for k in ("step_invite_msg", "step_value_msg", "step_followup_msg")):
                raise ValueError("The model returned incomplete outreach content.")
            return OutreachTemplate(
                campaign_id=campaign_id,
                step_invite_msg=res.get("step_invite_msg", "").strip(),
                step_value_msg=res.get("step_value_msg", "").strip(),
                step_followup_msg=res.get("step_followup_msg", "").strip(),
            )
        except Exception as e:
            raise RuntimeError("Outreach generation failed. Please retry.") from e
