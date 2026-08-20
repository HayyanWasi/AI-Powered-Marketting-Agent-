"""Tests for the Marketing Agent Orchestrator."""

import dataclasses
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.context import (
    BrandData,
    EventData,
    GenerationContext,
)
from src.agents.context_builder import ContextBuilder
from src.agents.orchestrator import Orchestrator
from src.models.llm import LLMResponse, TokenUsage


def _fake_llm() -> MagicMock:
    """LLM returning well-formed labeled responses (no network).

    Responds per prompt type: the strategy agent and the content generator
    expect different label sets.
    """
    strategy_text = (
        "USP_HOOK: The one event where you meet the people building the future.\n"
        "MESSAGING_PILLARS: Learn from leaders, High value, Limited seats\n"
        "OBJECTION_HANDLING: Worth my time? — Industry leaders attend; "
        "Is it free? — Yes, seats are limited\n"
        "CTA_HIERARCHY: Follow for updates, Register now"
    )
    content_text = (
        "VARIANT_A: Story variant.\n"
        "VARIANT_B: Value variant.\n"
        "VARIANT_C: Question variant?\n"
        "IMAGE_PROMPT: A branded event banner."
    )

    def _generate(request):
        text = strategy_text if request.prompt_name == "generate_strategy" else content_text
        return LLMResponse(
            text=text,
            token_usage=TokenUsage(),
            provider="openai",
            model="gpt-4o",
        )

    llm = MagicMock()
    llm.generate.side_effect = _generate
    return llm


def _fake_cloudflare() -> MagicMock:
    """Cloudflare returning a base64 image (no network)."""

    # Minimal 1x1 PNG
    img_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
        b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    service = MagicMock()
    service.img2img_model = "@cf/runwayml/stable-diffusion-v1-5-img2img"
    service.text2img_model = "@cf/black-forest-labs/flux-1-schnell"
    service.generate_from_reference = AsyncMock(return_value=img_bytes)
    service.generate_from_text = AsyncMock(return_value=img_bytes)
    service.download_reference = AsyncMock(return_value=b"fake_ref_bytes")
    service.__aenter__ = AsyncMock(return_value=service)
    service.__aexit__ = AsyncMock(return_value=None)
    return service


def _make_orchestrator() -> Orchestrator:
    """Orchestrator with all external-calling agents mocked."""
    return Orchestrator(
        llm_service=_fake_llm(),
        cloudflare_service=_fake_cloudflare(),
    )


class TestGenerationContext:
    def test_create_empty_context(self) -> None:
        ctx = GenerationContext()
        assert ctx.context_id is not None
        assert ctx.brand.company_name == ""
        assert ctx.guests == ()
        assert ctx.calendar == ()

    def test_create_context_with_brand(self) -> None:
        brand = BrandData(
            company_name="Test Corp",
            brand_guidelines="Professional tone",
            brand_tone="Friendly",
        )
        ctx = GenerationContext(brand=brand)
        assert ctx.brand.company_name == "Test Corp"
        assert ctx.brand.brand_guidelines == "Professional tone"

    def test_context_is_frozen(self) -> None:
        brand = BrandData(company_name="Test")
        ctx = GenerationContext(brand=brand)
        # BrandData is frozen — cannot modify
        try:
            brand.company_name = "Changed"
            assert False, "Should have raised FrozenInstanceError"
        except Exception:
            pass  # Expected

    def test_root_context_is_frozen(self) -> None:
        ctx = GenerationContext()
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.current_step = "changed"


class TestContextBuilder:
    def test_build_empty_context(self) -> None:
        builder = ContextBuilder()
        ctx = builder.build()
        assert ctx.brand.company_name == ""
        assert ctx.event.platforms == ()

    def test_build_with_event_details(self) -> None:
        builder = ContextBuilder()
        ctx = builder.build(
            event_name="AI Summit",
            event_date="2026-07-25",
            platforms=["linkedin", "instagram"],
        )
        assert ctx.event.event_name == "AI Summit"
        assert "linkedin" in ctx.event.platforms
        assert "instagram" in ctx.event.platforms


class TestOrchestrator:
    def _make_context(self) -> GenerationContext:
        brand = BrandData(
            company_name="Test Corp",
            brand_guidelines="Professional tone",
            brand_tone="Friendly",
        )
        event = EventData(
            event_name="Test Event",
            event_date="2026-07-25",
            platforms=("linkedin", "instagram"),
        )
        return GenerationContext(brand=brand, event=event)

    def test_orchestrator_creates(self) -> None:
        orch = Orchestrator()
        assert len(orch.agents) == 9

    async def test_full_workflow_execution(self) -> None:
        orch = _make_orchestrator()
        ctx = self._make_context()

        result = await orch.execute(ctx)

        assert result.success is True
        assert result.context.current_step == "complete"
        assert result.context.strategy.usp_hook != ""
        assert len(result.context.calendar) > 0
        assert len(result.context.content_drafts) > 0
        assert len(result.context.hashtags) > 0

    async def test_workflow_logs_execution(self) -> None:
        orch = _make_orchestrator()
        ctx = self._make_context()

        await orch.execute(ctx)

        assert len(orch.workflow_log) > 0
        assert all(entry["success"] for entry in orch.workflow_log)

    def test_strategy_approval(self) -> None:
        orch = Orchestrator()
        ctx = self._make_context()

        # Strategy starts unapproved
        from dataclasses import replace

        unapproved = replace(ctx, strategy=replace(ctx.strategy, approved=False))
        assert unapproved.strategy.approved is False

        # Approve it
        approved_ctx = orch.approve_strategy(unapproved)
        assert approved_ctx.strategy.approved is True

    async def test_content_rejection(self) -> None:
        orch = _make_orchestrator()
        ctx = self._make_context()

        result = await orch.execute(ctx)
        rejected_ctx = orch.reject_content(result.context, "Too generic")

        assert rejected_ctx.human_feedback == "Too generic"
        assert rejected_ctx.current_step == "content_rejected"

    async def test_workflow_fails_without_brand(self) -> None:
        orch = Orchestrator()
        ctx = GenerationContext()  # Empty brand

        result = await orch.execute(ctx)

        assert result.success is False
        assert "brand" in result.message.lower() or "Brand" in result.message

    async def test_content_has_three_variants(self) -> None:
        orch = _make_orchestrator()
        ctx = self._make_context()

        result = await orch.execute(ctx)

        for draft in result.context.content_drafts:
            assert draft.variant_a != ""
            assert draft.variant_b != ""
            assert draft.variant_c != ""

    async def test_calendar_has_multiple_slots(self) -> None:
        orch = _make_orchestrator()
        ctx = self._make_context()

        result = await orch.execute(ctx)

        # 2 platforms × 3 phases = 6 slots
        assert len(result.context.calendar) == 6
