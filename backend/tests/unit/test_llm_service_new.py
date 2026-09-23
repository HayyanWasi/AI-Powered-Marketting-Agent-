from unittest.mock import MagicMock

import pytest

from src.models.llm import LLMRequest, LLMResponse, TokenUsage
from src.services import llm_service as llm_service_module
from src.services.llm_service import (
    GeminiProvider,
    GroqProvider,
    LLMService,
    LLMServiceError,
)


def _make_groq_response(text="Hello", prompt_tokens=10, completion_tokens=20):
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = prompt_tokens + completion_tokens
    choice = MagicMock()
    choice.message.content = text
    completion = MagicMock()
    completion.choices = [choice]
    completion.usage = usage
    return completion


def _make_gemini_response(text="Hello from Gemini", prompt_tokens=5, completion_tokens=15):
    usage_meta = MagicMock()
    usage_meta.prompt_token_count = prompt_tokens
    usage_meta.candidates_token_count = completion_tokens
    usage_meta.total_token_count = prompt_tokens + completion_tokens
    response = MagicMock()
    response.text = text
    response.usage_metadata = usage_meta
    return response


class TestGroqProvider:
    def test_generate_success(self) -> None:
        client = MagicMock()
        client.chat.completions.create.return_value = _make_groq_response()
        provider = GroqProvider(client=client)
        result = provider.generate("system", "user")
        assert result.text == "Hello"
        assert result.provider == "groq"
        assert result.token_usage.prompt_tokens == 10
        assert client.chat.completions.create.call_args.kwargs["max_tokens"] == 2048


class TestGeminiProvider:
    def test_generate_success(self) -> None:
        model = MagicMock()
        model.generate_content.return_value = _make_gemini_response()
        provider = GeminiProvider(model=model)
        provider._initialized = True
        result = provider.generate("", "user")
        assert result.text == "Hello from Gemini"
        assert result.provider == "gemini"
        assert result.token_usage.prompt_tokens == 5

    def test_generate_stream(self) -> None:
        chunk1 = MagicMock()
        chunk1.text = "Hello"
        chunk2 = MagicMock()
        chunk2.text = " world"
        model = MagicMock()
        model.generate_content.return_value = [chunk1, chunk2]
        provider = GeminiProvider(model=model)
        provider._initialized = True
        chunks = list(provider.generate_stream("", "user"))
        assert len(chunks) == 3
        assert chunks[0].content == "Hello"
        assert chunks[0].finished is False
        assert chunks[2].finished is True


class TestLLMFailoverChain:
    def test_gemini_success(self):
        gemini = MagicMock()
        gemini.generate.return_value = LLMResponse(
            text="gemini_ok", token_usage=MagicMock(), provider="gemini", model="flash"
        )
        orouter = MagicMock()
        groq = MagicMock()

        svc = LLMService(gemini=gemini, openrouter=orouter, groq=groq)
        res = svc.generate(LLMRequest(user_prompt="hi"))
        assert res.text == "gemini_ok"
        gemini.generate.assert_called_once()
        orouter.generate.assert_not_called()
        groq.generate.assert_not_called()

    def test_gemini_fails_openrouter_success(self):
        gemini = MagicMock()
        gemini.generate.side_effect = Exception("gemini broke")
        orouter = MagicMock()
        orouter.generate.return_value = LLMResponse(
            text="orouter_ok", token_usage=MagicMock(), provider="openrouter", model="oss"
        )
        groq = MagicMock()

        svc = LLMService(gemini=gemini, openrouter=orouter, groq=groq)
        res = svc.generate(LLMRequest(user_prompt="hi"))
        assert res.text == "orouter_ok"
        gemini.generate.assert_called_once()
        orouter.generate.assert_called_once()
        groq.generate.assert_not_called()

    def test_gemini_fails_openrouter_missing_key_groq_success(self):
        gemini = MagicMock()
        gemini.generate.side_effect = Exception("gemini broke")
        orouter = MagicMock()
        orouter.generate.side_effect = Exception("missing API key")
        groq = MagicMock()
        groq.generate.return_value = LLMResponse(
            text="groq_ok", token_usage=MagicMock(), provider="groq", model="oss"
        )

        svc = LLMService(gemini=gemini, openrouter=orouter, groq=groq)
        res = svc.generate(LLMRequest(user_prompt="hi"))
        assert res.text == "groq_ok"
        gemini.generate.assert_called_once()
        orouter.generate.assert_called_once()
        groq.generate.assert_called_once()

    def test_all_fail(self):
        gemini = MagicMock()
        gemini.generate.side_effect = Exception("gemini broke")
        orouter = MagicMock()
        orouter.generate.side_effect = Exception("or broke")
        groq = MagicMock()
        groq.generate.side_effect = Exception("groq broke")

        svc = LLMService(gemini=gemini, openrouter=orouter, groq=groq)
        with pytest.raises(LLMServiceError, match="All LLM providers failed"):
            svc.generate(LLMRequest(user_prompt="hi"))


class TestLLMProviderRotation:
    def setup_method(self) -> None:
        llm_service_module._provider_rotation_index = 0
        llm_service_module._provider_unavailable_until.clear()

    @staticmethod
    def _success(provider: str) -> MagicMock:
        mock = MagicMock()
        mock.generate.return_value = LLMResponse(
            text=provider,
            token_usage=TokenUsage(provider=provider),
            provider=provider,
            model="test",
        )
        return mock

    def test_intra_tier_rotation_spreads_keys_and_keeps_tier_priority(self) -> None:
        """Rotation spreads across a tier's keys (TPM) but keeps tier priority.

        With two groq credentials plus one openrouter and one gemini, groq (the
        top tier) always answers, so gemini (least priority) is never reached;
        successive calls alternate between the two groq keys to spread load.
        """
        groq1 = self._success("groq")
        groq2 = self._success("groq")
        openrouter = self._success("openrouter")
        gemini = self._success("gemini")

        svc = LLMService(gemini=gemini, openrouter=openrouter, groq=groq1, rotate_providers=True)
        svc._chain = [
            ("groq", groq1, "m"),
            ("groq", groq2, "m"),
            ("openrouter", openrouter, "m"),
            ("gemini", gemini, "m"),
        ]

        results = [svc.generate(LLMRequest(user_prompt=f"request {index}")) for index in range(4)]

        # Tier priority holds: groq always wins; gemini (least) is never called.
        assert [r.provider for r in results] == ["groq", "groq", "groq", "groq"]
        gemini.generate.assert_not_called()
        openrouter.generate.assert_not_called()
        # Intra-tier rotation spread load evenly across BOTH groq credentials.
        assert groq1.generate.call_count == 2
        assert groq2.generate.call_count == 2

    def test_rate_limit_fails_over_without_retrying_same_provider(self) -> None:
        gemini = MagicMock()
        gemini.generate.side_effect = Exception("429 quota exceeded")
        openrouter = self._success("openrouter")
        groq = self._success("groq")

        result = LLMService(
            gemini=gemini,
            openrouter=openrouter,
            groq=groq,
            rotate_providers=True,
        ).generate(LLMRequest(user_prompt="request"))

        assert result.provider == "openrouter"
        assert gemini.generate.call_count == 1
        assert openrouter.generate.call_count == 1
        groq.generate.assert_not_called()

        # The next request skips the known rate-limited Gemini provider.
        next_result = LLMService(
            gemini=gemini,
            openrouter=openrouter,
            groq=groq,
            rotate_providers=True,
        ).generate(LLMRequest(user_prompt="next request"))
        assert next_result.provider == "openrouter"
        assert gemini.generate.call_count == 1
