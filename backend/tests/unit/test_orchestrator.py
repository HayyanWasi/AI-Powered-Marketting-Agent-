"""Tests for the Marketing Agent Orchestrator."""

from src.agents.context import (
    GenerationContext,
    BrandData,
    EventData,
    GuestData,
    StrategyData,
    ContentSlot,
    ContentDraft,
)
from src.agents.orchestrator import Orchestrator, WorkflowPhase
from src.agents.context_builder import ContextBuilder


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

    def test_full_workflow_execution(self) -> None:
        orch = Orchestrator()
        ctx = self._make_context()

        result = orch.execute(ctx)

        assert result.success is True
        assert result.context.current_step == "complete"
        assert result.context.strategy.usp_hook != ""
        assert len(result.context.calendar) > 0
        assert len(result.context.content_drafts) > 0
        assert len(result.context.hashtags) > 0

    def test_workflow_logs_execution(self) -> None:
        orch = Orchestrator()
        ctx = self._make_context()

        orch.execute(ctx)

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

    def test_content_rejection(self) -> None:
        orch = Orchestrator()
        ctx = self._make_context()

        result = orch.execute(ctx)
        rejected_ctx = orch.reject_content(result.context, "Too generic")

        assert rejected_ctx.human_feedback == "Too generic"
        assert rejected_ctx.current_step == "content_rejected"

    def test_workflow_fails_without_brand(self) -> None:
        orch = Orchestrator()
        ctx = GenerationContext()  # Empty brand

        result = orch.execute(ctx)

        assert result.success is False
        assert "brand" in result.message.lower() or "Brand" in result.message

    def test_content_has_three_variants(self) -> None:
        orch = Orchestrator()
        ctx = self._make_context()

        result = orch.execute(ctx)

        for draft in result.context.content_drafts:
            assert draft.variant_a != ""
            assert draft.variant_b != ""
            assert draft.variant_c != ""

    def test_calendar_has_multiple_slots(self) -> None:
        orch = Orchestrator()
        ctx = self._make_context()

        result = orch.execute(ctx)

        # 2 platforms × 3 phases = 6 slots
        assert len(result.context.calendar) == 6
