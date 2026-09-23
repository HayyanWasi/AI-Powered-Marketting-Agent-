"""Immutable canonical context for one campaign video generation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.brand_context import BrandContext
from src.modules.planning.models.campaign_plan import CampaignPlan

if TYPE_CHECKING:
    from src.services.campaign_context_service import CampaignInputs


class VideoGenerationContext(BaseModel):
    """Snapshot of trusted inputs used by both script and image generation."""

    model_config = ConfigDict(frozen=True)

    campaign_id: UUID
    owner_id: UUID
    brand: BrandContext
    campaign_type: str = ""
    campaign_name: str = ""
    objective: str = ""
    target_audience: str = ""
    value_proposition: str = ""
    cta_url: str = ""
    event_date: str = ""
    venue: str = ""
    guest: str = ""
    category: str = ""
    product_facts: str = ""
    plan_id: UUID
    plan_version: int
    positioning: str = ""
    unique_selling_proposition: str = ""
    messaging_pillars: tuple[str, ...] = ()
    strategy_tone: str = ""
    research_status: str = "not_requested"
    research_context: str = ""
    user_instruction: str = ""
    reference_image_urls: tuple[str, ...] = ()
    reference_images_used: bool = False

    @classmethod
    def from_sources(
        cls,
        *,
        inputs: CampaignInputs,
        plan: CampaignPlan,
        owner_id: UUID,
        user_instruction: str,
    ) -> VideoGenerationContext:
        intake = inputs.intake
        raw_campaign_type = intake.get("campaign_type")
        campaign_type = getattr(raw_campaign_type, "value", raw_campaign_type) or ""
        is_event = campaign_type in {"physical_event", "webinar"}
        has_guest = intake.get("has_guest") is True
        guest = " — ".join(
            str(intake.get(key)).strip()
            for key in ("guest_name", "guest_title")
            if is_event and has_guest and intake.get(key)
        )
        research = plan.source_brief.get("research_context") or {}
        research_text = json.dumps(research, sort_keys=True, ensure_ascii=False, default=str)
        # Keep prompts bounded while retaining the persisted research snapshot/status.
        if len(research_text) > 6000:
            research_text = research_text[:6000] + "…"
        audience = intake.get("target_audience") or (
            (intake.get("audience_profile") or {}).get("summary", "")
        )
        objective = intake.get("objective") or (
            inputs.campaign.goals.primary if inputs.campaign.goals else ""
        )
        return cls(
            campaign_id=inputs.campaign.id,
            owner_id=owner_id,
            brand=inputs.brand,
            campaign_type=str(campaign_type),
            campaign_name=str(
                intake.get("campaign_name")
                or intake.get("event_name")
                or inputs.campaign.name
                or ""
            ),
            objective=str(objective or ""),
            target_audience=str(audience or ""),
            value_proposition=str(
                intake.get("value_proposition") or intake.get("outcome_deliverable") or ""
            ),
            cta_url=str(intake.get("cta_url") or intake.get("registration_link") or ""),
            event_date=str(intake.get("event_date") or "") if is_event else "",
            venue=str(intake.get("venue") or "") if is_event else "",
            guest=guest,
            category=str(intake.get("category") or ""),
            product_facts=str(
                intake.get("product_facts") or intake.get("curriculum_breakdown") or ""
            ),
            plan_id=plan.plan_id,
            plan_version=plan.version,
            positioning=plan.core_strategy.positioning_statement,
            unique_selling_proposition=plan.core_strategy.unique_selling_proposition,
            messaging_pillars=plan.core_strategy.messaging_pillars,
            strategy_tone=plan.core_strategy.tone_of_voice,
            research_status=plan.research_status.value,
            research_context=research_text if research else "",
            user_instruction=user_instruction.strip(),
            reference_image_urls=inputs.brand.reference_image_urls,
            # Current Cloudflare/Pollinations endpoints are text-to-image only.
            reference_images_used=False,
        )

    def campaign_facts_prompt(self) -> str:
        facts = {
            "Campaign type": self.campaign_type,
            "Campaign name": self.campaign_name,
            "Objective": self.objective,
            "Target audience": self.target_audience,
            "Value proposition": self.value_proposition,
            "Canonical CTA": self.cta_url,
            "Category": self.category,
            "Product/service facts": self.product_facts,
            "Event date": self.event_date,
            "Venue": self.venue,
            "Confirmed guest": self.guest,
        }
        return "\n".join(f"{key}: {value}" for key, value in facts.items() if value)

    def strategy_prompt(self) -> str:
        strategy = {
            "Plan identity": f"{self.plan_id} version {self.plan_version}",
            "Positioning": self.positioning,
            "Unique selling proposition": self.unique_selling_proposition,
            "Messaging pillars": "; ".join(self.messaging_pillars),
            "Strategy tone": self.strategy_tone,
        }
        return "\n".join(f"{key}: {value}" for key, value in strategy.items() if value)

    def visual_direction_prompt(self) -> str:
        brand = self.brand
        fields = {
            "Company": brand.company_name,
            "Company/product identity": brand.description,
            "Industry": brand.industry,
            "Visual personality cues": "; ".join(brand.personality_traits),
            "Tone/style cues": brand.brand_tone,
            "Campaign": self.campaign_name,
            "Audience": self.target_audience,
            "Objective": self.objective,
            "Prohibited/negative guardrails": "; ".join(brand.negative_guardrails),
        }
        lines = [f"{key}: {value}" for key, value in fields.items() if value]
        lines.append("Keep the same product/subject identity, visual style, and environment across scenes.")
        if self.campaign_type not in {"physical_event", "webinar"}:
            lines.append(
                "Do not depict or mention an event venue, auditorium, workshop, session, guest, or attendees."
            )
        else:
            absent = []
            if not self.venue:
                absent.append("venue")
            if not self.guest:
                absent.append("guest")
            if not self.product_facts:
                absent.append("curriculum")
            absent.extend(("ticket price", "seat count"))
            lines.append("Do not invent absent event facts: " + ", ".join(absent) + ".")
        if self.reference_image_urls:
            lines.append(
                "Canonical reference images exist, but the active text-to-image providers do not support reference-image conditioning; they are not claimed as used."
            )
        return "\n".join(lines)
