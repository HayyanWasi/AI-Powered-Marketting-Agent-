"""Tests for the ContentGenerationAgent (LLM copy + image prompt).

The LLMService is mocked per constitution §Test-First.
"""

from unittest.mock import MagicMock

from src.agents.content_generator import ContentGenerationAgent
from src.agents.context import (
    BrandData,
    ContentSlot,
    EventData,
    GenerationContext,
    GuestData,
)
from src.models.llm import LLMResponse, TokenUsage


def _llm_returning(text: str) -> MagicMock:
    llm = MagicMock()
    llm.generate.return_value = LLMResponse(
        text=text,
        token_usage=TokenUsage(),
        provider="openai",
        model="gpt-4o",
    )
    return llm


def _slot() -> ContentSlot:
    return ContentSlot(
        slot_id="s1",
        date="2026-07-25",
        platform="linkedin",
        phase="teaser",
        theme="speaker reveal",
        format_type="single_image",
    )


def _context(**brand_kwargs) -> GenerationContext:
    brand = BrandData(company_name="Acme Corp", brand_tone="Confident", **brand_kwargs)
    event = EventData(event_name="AI Summit", event_date="2026-07-25", venue="Expo")
    guests = (GuestData(full_name="Jane Doe", biography="AI researcher."),)
    return GenerationContext(brand=brand, event=event, guests=guests, calendar=(_slot(),))


_GOOD_RESPONSE = """VARIANT_A: Story hook about the summit.
VARIANT_B: 3 reasons to attend: A, B, C.
VARIANT_C: What if you could meet Jane Doe?
IMAGE_PROMPT: A vibrant stage with a speaker under blue lights."""


class TestParsing:
    def test_parses_three_variants_and_image_prompt(self) -> None:
        agent = ContentGenerationAgent(llm_service=_llm_returning(_GOOD_RESPONSE))

        result = agent.execute(_context())

        assert result.success is True
        draft = result.context.content_drafts[0]
        assert draft.variant_a == "Story hook about the summit."
        assert draft.variant_b == "3 reasons to attend: A, B, C."
        assert draft.variant_c == "What if you could meet Jane Doe?"
        assert draft.image_prompt == "A vibrant stage with a speaker under blue lights."

    def test_multiline_variant_captured(self) -> None:
        text = "VARIANT_A: line one\nline two\n" "VARIANT_B: b\nVARIANT_C: c\nIMAGE_PROMPT: img"
        agent = ContentGenerationAgent(llm_service=_llm_returning(text))

        draft = agent.execute(_context()).context.content_drafts[0]

        assert draft.variant_a == "line one\nline two"

    def test_case_insensitive_labels(self) -> None:
        text = "variant_a: a\nvariant_b: b\nvariant_c: c\nimage_prompt: img"
        agent = ContentGenerationAgent(llm_service=_llm_returning(text))

        draft = agent.execute(_context()).context.content_drafts[0]

        assert draft.variant_a == "a"
        assert draft.image_prompt == "img"


class TestPromptContent:
    def test_prompt_includes_guests_and_brand(self) -> None:
        llm = _llm_returning(_GOOD_RESPONSE)
        agent = ContentGenerationAgent(llm_service=llm)

        agent.execute(_context())

        user_prompt = llm.generate.call_args.args[0].user_prompt
        assert "Jane Doe" in user_prompt
        assert "Acme Corp" in user_prompt
        assert "Confident" in user_prompt
        assert "AI Summit" in user_prompt


class TestFallback:
    def test_llm_failure_falls_back_to_placeholder(self) -> None:
        llm = MagicMock()
        llm.generate.side_effect = RuntimeError("provider down")
        agent = ContentGenerationAgent(llm_service=llm)

        result = agent.execute(_context())

        draft = result.context.content_drafts[0]
        assert result.success is True
        assert draft.variant_a != ""
        assert draft.variant_b != ""
        assert draft.variant_c != ""
        assert "AI Summit" in draft.variant_a

    def test_unparseable_response_falls_back(self) -> None:
        agent = ContentGenerationAgent(llm_service=_llm_returning("garbage no labels"))

        draft = agent.execute(_context()).context.content_drafts[0]

        assert draft.variant_a != ""

    def test_missing_image_prompt_uses_default(self) -> None:
        text = "VARIANT_A: a\nVARIANT_B: b\nVARIANT_C: c"
        agent = ContentGenerationAgent(llm_service=_llm_returning(text))

        draft = agent.execute(_context()).context.content_drafts[0]

        assert "AI Summit" in draft.image_prompt


class TestNoCalendar:
    def test_empty_calendar_fails(self) -> None:
        agent = ContentGenerationAgent(llm_service=_llm_returning(_GOOD_RESPONSE))
        ctx = GenerationContext(brand=BrandData(company_name="Acme"))

        result = agent.execute(ctx)

        assert result.success is False
