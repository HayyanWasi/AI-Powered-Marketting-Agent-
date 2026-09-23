from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.models.brand_context import BrandContext
from src.modules.linkedin.generators.content_context import ContentContextBuilder
from src.modules.linkedin.generators.post_generator import LinkedInPostGenerator
from src.modules.linkedin.models import ContentContext, ResearchedFact
from src.modules.planning.models.campaign_plan import CalendarSlot, CampaignPlan, ChannelPlan, CoreStrategy, Competitive
from src.modules.research.models.research_brief import ResearchBrief
from src.modules.research.services.llm_router import LLMRouterService


SENTINEL_BRAND = BrandContext(
    company_profile_id=uuid4(),
    company_name="LinkedIn Sentinel Brand",
    brand_tone="Direct, concise, practical",
    negative_guardrails=(
        "Never use buzzwords like revolutionary",
        "Never use rocket emojis",
        "Do not invent customer testimonials",
    ),
)

SENTINEL_CAMPAIGN = {
    "campaign_type": "app_launch",
    "campaign_name": "LinkedIn Sentinel App",
    "objective": "Acquire 5,000 active beta users",
    "value_proposition": "Real-time AI marketing orchestration without manual prompts",
    "cta_url": "https://sentinel.invalid/download-app",
    "target_audience": "B2B Marketing Leaders",
}

SENTINEL_PLAN = CampaignPlan(
    campaign_id=uuid4(),
    status="Approved",
    core_strategy=CoreStrategy(
        positioning_statement="The definitive autonomous campaign execution engine for B2B brands.",
        unique_selling_proposition="Zero-manual orchestration with verified real-world evidence.",
        tone_of_voice="Direct, concise, practical",
    ),
    competitive=Competitive(
        differentiation_angle="Web-grounded live intelligence vs static template tools.",
    ),
    channel_plan=ChannelPlan(
        calendar_slots=[
            CalendarSlot(
                slot_id="slot-sentinel-1",
                date="2026-10-15",
                theme="Autonomous Product Launch",
                messaging_pillar="AI Efficiency",
                cta="Download the Beta App",
            )
        ]
    ),
)


@pytest.mark.asyncio
async def test_content_context_mapping_and_prompt_propagation():
    """Verify that stored plan, brand context, and campaign facts propagate to LLM prompt."""
    slot = SENTINEL_PLAN.channel_plan.calendar_slots[0]
    
    # 1. Test ContentContextBuilder maps all fields faithfully
    ctx = ContentContextBuilder.build_context(
        slot=slot,
        plan=SENTINEL_PLAN,
        brief=None,
        brand=SENTINEL_BRAND,
        campaign_type=SENTINEL_CAMPAIGN["campaign_type"],
        campaign_name=SENTINEL_CAMPAIGN["campaign_name"],
        objective=SENTINEL_CAMPAIGN["objective"],
        value_proposition=SENTINEL_CAMPAIGN["value_proposition"],
        cta_url=SENTINEL_CAMPAIGN["cta_url"],
        target_audience=SENTINEL_CAMPAIGN["target_audience"],
    )

    assert ctx.brand == SENTINEL_BRAND
    assert ctx.campaign_type == "app_launch"
    assert ctx.campaign_name == "LinkedIn Sentinel App"
    assert ctx.objective == "Acquire 5,000 active beta users"
    assert ctx.value_proposition == "Real-time AI marketing orchestration without manual prompts"
    assert ctx.cta_url == "https://sentinel.invalid/download-app"
    assert ctx.target_audience == "B2B Marketing Leaders"
    assert ctx.usp == "Zero-manual orchestration with verified real-world evidence."
    assert ctx.differentiation_angle == "Web-grounded live intelligence vs static template tools."
    assert ctx.positioning == "The definitive autonomous campaign execution engine for B2B brands."

    # 2. Test prompt generation preserves sentinels and avoids event fabrication
    mock_llm = AsyncMock(spec=LLMRouterService)
    mock_llm.generate_json.return_value = {
        "hook": "Engineered for speed.",
        "body": "Autonomous orchestration is here.",
        "cta": "Download now.",
    }

    generator = LinkedInPostGenerator(llm_router=mock_llm)
    await generator._generate_single_post(
        campaign_id=SENTINEL_PLAN.campaign_id,
        ctx=ctx,
        scheduled_at=datetime.datetime.now(datetime.UTC),
    )

    call_args = mock_llm.generate_json.call_args
    assert call_args is not None
    system_prompt, user_prompt = call_args[0]

    # Explicit sections check
    assert "### BRAND IDENTITY" in user_prompt
    assert "### CAMPAIGN FACTS" in user_prompt
    assert "### CAMPAIGN STRATEGY" in user_prompt
    assert "### RESEARCH EVIDENCE" in user_prompt

    # Brand sentinels
    assert "LinkedIn Sentinel Brand" in user_prompt
    assert "Direct, concise, practical" in user_prompt
    for guardrail in SENTINEL_BRAND.negative_guardrails:
        assert guardrail in user_prompt

    # Campaign facts sentinels
    assert "app_launch" in user_prompt
    assert "LinkedIn Sentinel App" in user_prompt
    assert "Acquire 5,000 active beta users" in user_prompt
    assert "Real-time AI marketing orchestration without manual prompts" in user_prompt
    assert "https://sentinel.invalid/download-app" in user_prompt
    assert "B2B Marketing Leaders" in user_prompt

    # Strategy sentinels
    assert "The definitive autonomous campaign execution engine for B2B brands." in user_prompt
    assert "Zero-manual orchestration with verified real-world evidence." in user_prompt
    assert "Web-grounded live intelligence vs static template tools." in user_prompt
    assert "Autonomous Product Launch" in user_prompt
    assert "AI Efficiency" in user_prompt

    # App launch neutrality / No event fabrication check
    lower_prompt = user_prompt.lower()
    assert "venue" not in lower_prompt
    assert "guest speaker" not in lower_prompt
    assert "keynote" not in lower_prompt
    assert "seats" not in lower_prompt
    assert "curriculum" not in lower_prompt


@pytest.mark.asyncio
async def test_missing_plan_produces_truthful_error():
    """Verify that generating LinkedIn content without a stored plan produces an actionable error."""
    from src.api.v1.linkedin import generate_campaign_content
    from src.api.dependencies import AuthenticatedUser
    from src.modules.planning.repositories.plan_repository import PlanNotFoundError

    dummy_campaign_id = uuid4()
    mock_user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])

    with patch("src.api.v1.linkedin.CampaignContextResolver.resolve") as mock_resolve:
        mock_resolve.return_value = AsyncMock()
        with patch("src.api.v1.linkedin.PlanRefinementService.get_plan") as mock_get_plan:
            mock_get_plan.side_effect = PlanNotFoundError("No plan found for campaign.")

            with pytest.raises(HTTPException) as exc_info:
                await generate_campaign_content(
                    campaign_id=dummy_campaign_id,
                    user=mock_user,
                )

            assert exc_info.value.status_code == 409
            assert "Draft a campaign plan before generating LinkedIn content." in exc_info.value.detail
