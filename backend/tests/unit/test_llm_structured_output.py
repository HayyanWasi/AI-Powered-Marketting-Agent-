"""Targeted unit tests verifying structured LLM output reliability (Scenarios A through I)."""

import json
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from src.models.llm import LLMRequest, LLMResponse, TokenUsage
from src.modules.planning.agents import panel
from src.modules.planning.models.brief import PlanBrief
from src.services.llm_service import (
    GeminiProvider,
    GroqProvider,
    LLMProviderError,
    LLMService,
    LLMServiceError,
    OpenRouterProvider,
)


class SampleSchema(BaseModel):
    name: str
    score: int


# ── Scenario A: Native JSON mode parameter propagation ───────────────────────

class TestScenarioANativeJsonMode:
    def test_gemini_passes_response_mime_type(self) -> None:
        model = MagicMock()
        fake_response = MagicMock()
        fake_response.text = '{"name": "test", "score": 10}'
        fake_response.usage_metadata = None
        fake_response.candidates = [MagicMock(finish_reason="STOP")]
        model.generate_content.return_value = fake_response

        provider = GeminiProvider(model=model)
        provider._initialized = True
        provider.generate("", "user", json_mode=True)

        call_kwargs = model.generate_content.call_args.kwargs
        assert call_kwargs["generation_config"]["response_mime_type"] == "application/json"

    def test_gemini_fallback_when_response_mime_type_unsupported(self) -> None:
        model = MagicMock()
        fake_response = MagicMock()
        fake_response.text = '{"name": "test", "score": 10}'
        fake_response.usage_metadata = None
        fake_response.candidates = []

        def side_effect(*args, **kwargs):
            if "response_mime_type" in kwargs.get("generation_config", {}):
                raise Exception("Invalid argument: response_mime_type")
            return fake_response

        model.generate_content.side_effect = side_effect
        provider = GeminiProvider(model=model)
        provider._initialized = True
        res = provider.generate("", "user", json_mode=True)
        assert res.text == '{"name": "test", "score": 10}'
        assert model.generate_content.call_count == 2

    def test_groq_passes_response_format(self) -> None:
        client = MagicMock()
        choice = MagicMock()
        choice.message.content = '{"name": "test", "score": 10}'
        choice.finish_reason = "stop"
        completion = MagicMock()
        completion.choices = [choice]
        completion.usage = None
        client.chat.completions.create.return_value = completion

        provider = GroqProvider(client=client)
        provider._initialized = True
        provider.generate("", "user", json_mode=True)

        call_kwargs = client.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}

    def test_groq_fallback_when_response_format_unsupported(self) -> None:
        client = MagicMock()
        choice = MagicMock()
        choice.message.content = '{"name": "test", "score": 10}'
        choice.finish_reason = "stop"
        completion = MagicMock()
        completion.choices = [choice]
        completion.usage = None

        def side_effect(**kwargs):
            if "response_format" in kwargs:
                raise Exception("Unsupported parameter: response_format")
            return completion

        client.chat.completions.create.side_effect = side_effect
        provider = GroqProvider(client=client)
        provider._initialized = True
        res = provider.generate("", "user", json_mode=True)
        assert res.text == '{"name": "test", "score": 10}'
        assert client.chat.completions.create.call_count == 2

    def test_openrouter_passes_response_format(self) -> None:
        client = MagicMock()
        choice = MagicMock()
        choice.message.content = '{"name": "test", "score": 10}'
        choice.finish_reason = "stop"
        completion = MagicMock()
        completion.choices = [choice]
        completion.usage = None
        client.chat.completions.create.return_value = completion

        provider = OpenRouterProvider(client=client)
        provider._initialized = True
        provider.generate("", "user", json_mode=True)

        call_kwargs = client.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}


# ── Scenario B: Provider captures finish_reason ──────────────────────────────

class TestScenarioBFinishReasonCapture:
    def test_gemini_captures_finish_reason(self) -> None:
        model = MagicMock()
        candidate = MagicMock()
        candidate.finish_reason = "MAX_TOKENS"
        fake_response = MagicMock(text="text", usage_metadata=None, candidates=[candidate])
        model.generate_content.return_value = fake_response

        provider = GeminiProvider(model=model)
        provider._initialized = True
        res = provider.generate("", "user")
        assert res.finish_reason == "MAX_TOKENS"

    def test_groq_captures_finish_reason(self) -> None:
        client = MagicMock()
        choice = MagicMock()
        choice.message.content = "text"
        choice.finish_reason = "length"
        completion = MagicMock(choices=[choice], usage=None)
        client.chat.completions.create.return_value = completion

        provider = GroqProvider(client=client)
        provider._initialized = True
        res = provider.generate("", "user")
        assert res.finish_reason == "length"

    def test_openrouter_captures_finish_reason(self) -> None:
        client = MagicMock()
        choice = MagicMock()
        choice.message.content = "text"
        choice.finish_reason = "stop"
        completion = MagicMock(choices=[choice], usage=None)
        client.chat.completions.create.return_value = completion

        provider = OpenRouterProvider(client=client)
        provider._initialized = True
        res = provider.generate("", "user")
        assert res.finish_reason == "stop"


# ── Scenario C: Truncation detection (no repair retry) ─────────────────────────

class TestScenarioCTruncationDetection:
    def test_direct_truncation_validation_raises(self) -> None:
        from src.services.llm_service import _validate_structured_response
        resp = LLMResponse(
            text='{"name": "partial',
            token_usage=TokenUsage(),
            provider="gemini",
            model="model",
            finish_reason="length",
        )
        with pytest.raises(LLMProviderError, match="truncated due to token limit"):
            _validate_structured_response(resp, LLMRequest(user_prompt="hi", json_mode=True), "gemini")

    def test_truncation_detected_and_skips_repair_retry(self) -> None:
        gemini = MagicMock()
        gemini.generate.return_value = LLMResponse(
            text='{"name": "partial',
            token_usage=TokenUsage(),
            provider="gemini",
            model="model",
            finish_reason="length",
        )
        openrouter = MagicMock()
        openrouter.generate.side_effect = LLMProviderError("openrouter", "unavailable")
        groq = MagicMock()
        groq.generate.side_effect = LLMProviderError("groq", "unavailable")
        svc = LLMService(gemini=gemini, openrouter=openrouter, groq=groq, rotate_providers=False)

        # Because it's truncated, it should fail without retrying gemini
        with pytest.raises(LLMServiceError):
            svc.generate(LLMRequest(user_prompt="hi", json_mode=True, output_schema=SampleSchema))

        assert gemini.generate.call_count == 1


# ── Scenario D: In-service structured validation succeeds ─────────────────────

class TestScenarioDStructuredValidation:
    def test_valid_json_and_schema_succeeds(self) -> None:
        gemini = MagicMock()
        gemini.generate.return_value = LLMResponse(
            text='{"name": "Acme", "score": 99}',
            token_usage=TokenUsage(),
            provider="gemini",
            model="model",
            finish_reason="stop",
        )
        svc = LLMService(gemini=gemini, openrouter=MagicMock(), groq=MagicMock(), rotate_providers=False)
        res = svc.generate(LLMRequest(user_prompt="hi", json_mode=True, output_schema=SampleSchema))
        assert res.provider == "gemini"
        assert json.loads(res.text)["name"] == "Acme"
        assert gemini.generate.call_count == 1


# ── Scenario E: Single repair retry on invalid JSON / schema ──────────────────

class TestScenarioERepairRetry:
    def test_single_repair_retry_succeeds(self) -> None:
        gemini = MagicMock()
        gemini.generate.side_effect = [
            LLMResponse(
                text="Here is the strategy: not json",
                token_usage=TokenUsage(),
                provider="gemini",
                model="model",
                finish_reason="stop",
            ),
            LLMResponse(
                text='{"name": "Fixed", "score": 100}',
                token_usage=TokenUsage(),
                provider="gemini",
                model="model",
                finish_reason="stop",
            ),
        ]
        svc = LLMService(gemini=gemini, openrouter=MagicMock(), groq=MagicMock(), rotate_providers=False)
        res = svc.generate(LLMRequest(user_prompt="original prompt", json_mode=True, output_schema=SampleSchema))
        assert res.provider == "gemini"
        assert json.loads(res.text)["name"] == "Fixed"
        assert gemini.generate.call_count == 2

        # Verify repair prompt appends the exact instruction
        second_call_prompt = gemini.generate.call_args_list[1][0][1]
        assert "Return only valid JSON matching the required schema. No markdown, commentary, or code fences." in second_call_prompt


# ── Scenario F: Provider failover on persistent invalid JSON ─────────────────

class TestScenarioFFailoverOnInvalidJson:
    def test_provider_fails_after_repair_and_fails_over_to_next(self) -> None:
        # Provider 1 (gemini): returns non-JSON twice (initial + repair)
        gemini = MagicMock()
        gemini.generate.side_effect = [
            LLMResponse(text="not json 1", token_usage=TokenUsage(), provider="gemini", model="g"),
            LLMResponse(text="not json 2", token_usage=TokenUsage(), provider="gemini", model="g"),
        ]
        # Provider 2 (openrouter): returns valid JSON on first attempt
        openrouter = MagicMock()
        openrouter.generate.return_value = LLMResponse(
            text='{"name": "OpenRouterSuccess", "score": 88}',
            token_usage=TokenUsage(),
            provider="openrouter",
            model="or",
            finish_reason="stop",
        )
        groq = MagicMock()

        svc = LLMService(gemini=gemini, openrouter=openrouter, groq=groq, rotate_providers=False)
        res = svc.generate(LLMRequest(user_prompt="prompt", json_mode=True, output_schema=SampleSchema))

        assert res.provider == "openrouter"
        assert json.loads(res.text)["name"] == "OpenRouterSuccess"
        assert gemini.generate.call_count == 2
        assert openrouter.generate.call_count == 1
        groq.generate.assert_not_called()


# ── Scenario G: All providers fail ────────────────────────────────────────────

class TestScenarioGAllProvidersFail:
    def test_all_providers_fail_raises_llmserviceerror(self) -> None:
        gemini = MagicMock()
        gemini.generate.side_effect = [
            LLMResponse(text="bad 1", token_usage=TokenUsage(), provider="gemini", model="g"),
            LLMResponse(text="bad 2", token_usage=TokenUsage(), provider="gemini", model="g"),
        ]
        openrouter = MagicMock()
        openrouter.generate.side_effect = [
            LLMResponse(text="bad 3", token_usage=TokenUsage(), provider="openrouter", model="or"),
            LLMResponse(text="bad 4", token_usage=TokenUsage(), provider="openrouter", model="or"),
        ]
        groq = MagicMock()
        groq.generate.side_effect = [
            LLMResponse(text="bad 5", token_usage=TokenUsage(), provider="groq", model="groq"),
            LLMResponse(text="bad 6", token_usage=TokenUsage(), provider="groq", model="groq"),
        ]

        svc = LLMService(gemini=gemini, openrouter=openrouter, groq=groq, rotate_providers=False)
        with pytest.raises(LLMServiceError, match="All LLM providers failed"):
            svc.generate(LLMRequest(user_prompt="prompt", json_mode=True, output_schema=SampleSchema))


# ── Scenario H: Specialist panel failure rule preserved ───────────────────────

class TestScenarioHSpecialistFailurePreserved:
    @pytest.mark.asyncio
    async def test_specialist_aborts_when_llm_fails(self) -> None:
        fake_service = MagicMock()
        fake_service.generate.side_effect = LLMServiceError("All LLM providers failed. Last error: 429")

        with pytest.raises(LLMServiceError, match="All LLM providers failed"):
            await panel.ask_json(
                "plan_competitive",
                {"user_goal": "Goal"},
                llm=fake_service,
            )


# ── Scenario I: PlanBrief.to_template_vars deduplication ──────────────────────

class TestScenarioIResearchDeduplication:
    def test_research_findings_not_duplicated(self) -> None:
        brief = PlanBrief(
            user_goal="Test goal",
            research_context={
                "research_brief": {
                    "market": {"key_findings": ["Market finding alpha", "Market finding beta"]},
                    "competitor": {"key_findings": ["Competitor finding gamma"]},
                },
                "evidence_graph": {"nodes": {"node1": {}}},
            },
        )
        vars_dict = brief.to_template_vars()
        research_text = vars_dict.get("research", "")

        assert "Market finding alpha" in research_text
        assert research_text.count("Market finding alpha") == 1
        assert research_text.count("Competitor finding gamma") == 1
