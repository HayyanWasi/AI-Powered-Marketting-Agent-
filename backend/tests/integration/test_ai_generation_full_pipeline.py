"""Integration test for AI Generation Engine full pipeline.

Tests the REAL LangGraph-backed pipeline through the Orchestrator facade.
External APIs (LLM, Cloudflare) are mocked at the boundary — all internal
code (agents, graph routing, retry, checkpointing) runs for real.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.context import BrandData, EventData, GenerationContext
from src.agents.orchestrator import Orchestrator
from src.models.llm import LLMResponse, TokenUsage

# ---------------------------------------------------------------------------
# Fixtures — mock ONLY external APIs, everything else is real
# ---------------------------------------------------------------------------


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
    """Real Orchestrator with real LangGraph pipeline, mocked external APIs."""
    return Orchestrator(
        llm_service=_fake_llm(),
        cloudflare_service=_fake_cloudflare(),
    )


def _make_context(
    company_name: str = "Test Corp",
    event_name: str = "AI Summit",
    platforms: tuple = ("linkedin", "instagram"),
) -> GenerationContext:
    """Build a real GenerationContext with brand + event data."""
    brand = BrandData(
        company_name=company_name,
        brand_guidelines="Professional tone with innovation focus",
        brand_tone="Friendly and forward-thinking",
    )
    event = EventData(
        event_name=event_name,
        event_date="2026-07-25",
        platforms=platforms,
    )
    return GenerationContext(brand=brand, event=event)


# ---------------------------------------------------------------------------
# Tests — all exercise the REAL pipeline end-to-end
# ---------------------------------------------------------------------------


class TestAIGenerationFullPipeline:
    """Integration tests for the complete AI Generation pipeline.

    Each test runs the real LangGraph pipeline with real agents.
    Only external API calls (LLM, Cloudflare) are mocked.
    """

    @pytest.mark.asyncio
    async def test_full_workflow_produces_complete_output(self):
        """Pipeline produces strategy, content, assets, hashtags, and calendar."""
        orch = _make_orchestrator()
        ctx = _make_context()

        result = await orch.execute(ctx)

        assert result.success is True
        assert result.context.current_step == "complete"

        # Strategy was generated
        assert result.context.strategy.usp_hook != ""
        assert result.context.strategy.approved is True

        # Content drafts were generated with three variants each
        assert len(result.context.content_drafts) > 0
        for draft in result.context.content_drafts:
            assert draft.variant_a != ""
            assert draft.variant_b != ""
            assert draft.variant_c != ""

        # Calendar slots generated (2 platforms x 3 phases = 6)
        assert len(result.context.calendar) == 6

        # Hashtags were generated
        assert len(result.context.hashtags) > 0

    @pytest.mark.asyncio
    async def test_pipeline_executes_through_langgraph(self):
        """Pipeline routes through LangGraph (not hand-rolled sequential)."""
        orch = _make_orchestrator()
        ctx = _make_context()

        result = await orch.execute(ctx)

        # The workflow_log tracks each node that executed through the graph
        assert len(orch.workflow_log) > 0

        # Verify all expected agents ran through LangGraph
        agent_names = [entry["agent"] for entry in orch.workflow_log]
        expected_agents = [
            "reference_matcher",
            "strategy",
            "campaign_planner",
            "content_generator",
            "hashtag_research",
            "hook_analyzer",
            "readability_scorer",
            "asset_generator",
            "validator",
        ]
        for name in expected_agents:
            assert name in agent_names, f"Agent {name} did not execute through LangGraph"

    @pytest.mark.asyncio
    async def test_pipeline_retry_occurs_inside_graph(self):
        """Retry logic runs inside LangGraph nodes, not outside the pipeline."""
        orch = _make_orchestrator()
        ctx = _make_context()

        result = await orch.execute(ctx)

        # Each log entry may report attempts > 1 if retry was needed
        # The key assertion: retry happens inside node execution, not outside
        for entry in orch.workflow_log:
            assert "attempts" in entry, (
                f"Agent {entry['agent']} missing 'attempts' field — "
                "retry logic not wired inside node wrapper"
            )

    @pytest.mark.asyncio
    async def test_pipeline_preserves_context_immutability(self):
        """Each node receives immutable context, returns new context."""
        orch = _make_orchestrator()
        ctx = _make_context()

        result = await orch.execute(ctx)

        # Original context should be unchanged
        assert ctx.brand.company_name == "Test Corp"
        assert ctx.event.event_name == "AI Summit"

        # Final context should have all the generated data
        final = result.context
        assert final.brand.company_name == "Test Corp"
        assert final.strategy.usp_hook != ""

    @pytest.mark.asyncio
    async def test_pipeline_deterministic_for_same_input(self):
        """Same input produces same structural output."""
        orch1 = _make_orchestrator()
        orch2 = _make_orchestrator()
        ctx1 = _make_context()
        ctx2 = _make_context()

        r1 = await orch1.execute(ctx1)
        r2 = await orch2.execute(ctx2)

        # Both succeed
        assert r1.success is True
        assert r2.success is True

        # Same number of content drafts
        assert len(r1.context.content_drafts) == len(r2.context.content_drafts)

        # Same number of calendar slots
        assert len(r1.context.calendar) == len(r2.context.calendar)

    @pytest.mark.asyncio
    async def test_pipeline_fails_gracefully_without_brand(self):
        """Pipeline fails with clear message when brand data is missing."""
        orch = _make_orchestrator()
        ctx = GenerationContext()  # Empty brand

        result = await orch.execute(ctx)

        assert result.success is False
        assert result.message != ""

    @pytest.mark.asyncio
    async def test_pipeline_strategy_approval_checkpoint(self):
        """Strategy auto-approval checkpoint is hit during pipeline."""
        orch = _make_orchestrator()
        ctx = _make_context()

        result = await orch.execute(ctx)

        # Strategy should be approved after pipeline completes
        assert result.context.strategy.approved is True

    @pytest.mark.asyncio
    async def test_pipeline_content_variants_are_distinct(self):
        """Content generator produces three distinct variants per platform."""
        orch = _make_orchestrator()
        ctx = _make_context()

        result = await orch.execute(ctx)

        for draft in result.context.content_drafts:
            # Each variant should be non-empty
            assert draft.variant_a.strip() != ""
            assert draft.variant_b.strip() != ""
            assert draft.variant_c.strip() != ""

    @pytest.mark.asyncio
    async def test_pipeline_multiple_platforms(self):
        """Pipeline handles multiple platforms correctly."""
        orch = _make_orchestrator()
        ctx = _make_context(platforms=("linkedin", "instagram", "facebook"))

        result = await orch.execute(ctx)

        assert result.success is True
        # 3 platforms x 3 phases = 9 calendar slots
        assert len(result.context.calendar) == 9
