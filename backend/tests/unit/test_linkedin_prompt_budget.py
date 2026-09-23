import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.models.brand_context import BrandContext
from src.modules.linkedin.generators.post_generator import (
    MAX_PROMPT_CHARS,
    PROMPT_BUDGET_MARGIN,
    LinkedInPostGenerator,
)
from src.modules.linkedin.models import ContentContext, ResearchedFact
from src.modules.research.services.llm_router import LLMRouterService

TONE_SENTINEL = "SENTINEL_BRAND_TONE"
GUARDRAIL_SENTINEL = "NEVER_USE_SENTINEL_PHRASE"


def _brand(**overrides) -> BrandContext:
    values = {
        "company_profile_id": uuid4(),
        "company_name": "GlowBook",
        "website": "https://glowbook.invalid",
        "industry": "Mobile software",
        "description": "A booking app for independent beauty professionals.",
        "target_audience": "Independent beauty professionals",
        "track_record": "Used by early access salons.",
        "specializations": ("Scheduling", "Client management"),
        "brand_tone": TONE_SENTINEL,
        "personality_traits": ("clear", "supportive"),
        "sample_voice": "Spend less time managing appointments.",
        "guidelines": "Write plainly and avoid unsupported claims.",
        "negative_guardrails": (GUARDRAIL_SENTINEL, "Never invent metrics"),
    }
    values.update(overrides)
    return BrandContext(**values)


def _context(**overrides) -> ContentContext:
    values = {
        "slot_id": "slot-1",
        "slot_date": "2026-10-10",
        "theme": "Simpler booking",
        "messaging_pillar": "Save administrative time",
        "cta": "Download GlowBook",
        "tone_of_voice": "Helpful",
        "brand": _brand(),
        "positioning": "The simple booking companion",
        "differentiation_angle": "Built for independent professionals",
        "usp": "Manage bookings from one app",
        "campaign_type": "app_launch",
        "campaign_name": "GlowBook Launch",
        "objective": "Acquire app downloads",
        "value_proposition": "Simplify appointment management",
        "target_audience": "Independent beauty professionals",
        "cta_url": "https://glowbook.invalid/download",
        "product_facts": "Mobile booking and client management",
    }
    values.update(overrides)
    return ContentContext(**values)


async def _render_prompt(ctx: ContentContext) -> tuple[str, AsyncMock]:
    llm = AsyncMock(spec=LLMRouterService)
    llm.generate_json.return_value = {
        "hook": "Test hook",
        "body": "Test body",
        "cta": "Test CTA",
    }
    generator = LinkedInPostGenerator(llm_router=llm)
    await generator._generate_single_post(
        campaign_id=uuid4(),
        ctx=ctx,
        scheduled_at=datetime.datetime.now(datetime.UTC),
    )
    return llm.generate_json.call_args.args[1], llm


def _assert_authoritative_context(prompt: str) -> None:
    assert "Company: GlowBook" in prompt
    assert f"Brand tone / writing style: {TONE_SENTINEL}" in prompt
    assert "Brand guidelines: Write plainly and avoid unsupported claims." in prompt
    assert GUARDRAIL_SENTINEL in prompt
    assert "Campaign Name: GlowBook Launch" in prompt
    assert "Objective: Acquire app downloads" in prompt
    assert "CTA / Destination URL: https://glowbook.invalid/download" in prompt


@pytest.mark.asyncio
async def test_normal_prompt_keeps_all_sections() -> None:
    prompt, _ = await _render_prompt(_context())

    _assert_authoritative_context(prompt)
    assert "### BRAND IDENTITY" in prompt
    assert "Company description: A booking app" in prompt
    assert "### CAMPAIGN FACTS" in prompt
    assert "### CAMPAIGN STRATEGY" in prompt
    assert "Positioning: The simple booking companion" in prompt
    assert "### RESEARCH EVIDENCE" in prompt
    assert "### INSTRUCTIONS" in prompt


@pytest.mark.asyncio
async def test_huge_research_is_trimmed_before_brand_rules() -> None:
    evidence = ResearchedFact(
        fact_id="research-1",
        dimension="market",
        claim="RESEARCH_START " + "r" * 300000 + " RESEARCH_END",
        quote="Verified snippet",
        source_url="https://research.invalid/source",
        confidence_score=4.0,
    )
    prompt, _ = await _render_prompt(_context(researched_facts=(evidence,)))

    _assert_authoritative_context(prompt)
    assert "RESEARCH_START" in prompt
    assert "RESEARCH_END" not in prompt
    assert "[FIELD TRUNCATED]" in prompt
    assert len(prompt) <= MAX_PROMPT_CHARS - PROMPT_BUDGET_MARGIN


@pytest.mark.asyncio
async def test_huge_optional_brand_content_is_safely_trimmed() -> None:
    brand = _brand(
        description="DESCRIPTION_START " + "d" * 300000 + " DESCRIPTION_END",
        track_record="TRACK_RECORD_SENTINEL",
    )
    prompt, _ = await _render_prompt(_context(brand=brand))

    _assert_authoritative_context(prompt)
    assert "DESCRIPTION_START" in prompt
    assert "DESCRIPTION_END" not in prompt
    assert "[FIELD TRUNCATED]" in prompt
    assert len(prompt) <= MAX_PROMPT_CHARS - PROMPT_BUDGET_MARGIN


@pytest.mark.asyncio
async def test_huge_strategy_is_trimmed_after_authoritative_context() -> None:
    prompt, _ = await _render_prompt(
        _context(positioning="STRATEGY_START " + "s" * 300000 + " STRATEGY_END")
    )

    _assert_authoritative_context(prompt)
    assert "STRATEGY_START" in prompt
    assert "STRATEGY_END" not in prompt
    assert "[FIELD TRUNCATED]" in prompt
    assert len(prompt) <= MAX_PROMPT_CHARS - PROMPT_BUDGET_MARGIN


@pytest.mark.asyncio
async def test_oversized_mandatory_context_fails_before_llm_call() -> None:
    llm = AsyncMock(spec=LLMRouterService)
    generator = LinkedInPostGenerator(llm_router=llm)
    ctx = _context(
        brand=_brand(guidelines="GUIDELINES_START " + "g" * MAX_PROMPT_CHARS + " GUIDELINES_END")
    )

    with pytest.raises(
        RuntimeError,
        match="Required campaign and brand context exceeds the supported LinkedIn generation context",
    ):
        await generator._generate_single_post(uuid4(), ctx)

    llm.generate_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_app_launch_does_not_gain_event_assumptions() -> None:
    prompt, _ = await _render_prompt(_context())

    assert "Venue:" not in prompt
    assert "Event Date:" not in prompt
    assert "Featured Guest/Speaker:" not in prompt
    assert "Pricing:" not in prompt
    assert "seats" not in prompt.lower()
    assert "curriculum" not in prompt.lower()
