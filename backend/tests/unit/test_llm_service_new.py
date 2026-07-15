from unittest.mock import MagicMock

import pytest

from src.config.prompts import PROMPT_TEMPLATES
from src.models.llm import LLMRequest, LLMResponse, StreamChunk, TokenUsage
from src.services.llm_service import (
    LLMProviderError,
    LLMService,
    LLMServiceError,
    LLMTemplateNotFoundError,
    OpenAIProvider,
    GeminiProvider,
)


def _make_openai_response(text="Hello", prompt_tokens=10, completion_tokens=20):
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


class TestOpenAIProvider:
    def test_generate_success(self) -> None:
        client = MagicMock()
        client.chat.completions.create.return_value = _make_openai_response()
        provider = OpenAIProvider(client=client)
        result = provider.generate("system", "user")
        assert result.text == "Hello"
        assert result.provider == "openai"
        assert result.token_usage.prompt_tokens == 10

    def test_generate_stream(self) -> None:
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="Hi"), finish_reason=None)]
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content=" there"), finish_reason="stop")]
        client = MagicMock()
        client.chat.completions.create.return_value = [chunk1, chunk2]
        provider = OpenAIProvider(client=client)
        chunks = list(provider.generate_stream("system", "user"))
        assert len(chunks) == 2
        assert chunks[0].content == "Hi"
        assert chunks[0].finished is False
        assert chunks[1].content == " there"
        assert chunks[1].finished is True


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


class TestLLMServiceGenerate:
    def setup_method(self) -> None:
        PROMPT_TEMPLATES.clear()

    def test_generate_primary_success(self) -> None:
        primary = MagicMock()
        primary.generate.return_value = LLMResponse(
            text="Hi", token_usage=TokenUsage(provider="openai"), provider="openai", model="gpt-4o"
        )
        service = LLMService(primary=primary)
        req = LLMRequest(user_prompt="hello")
        result = service.generate(req)
        assert result.text == "Hi"
        assert result.provider == "openai"
        primary.generate.assert_called_once()

    def test_generate_fallback_on_transient_error(self) -> None:
        primary = MagicMock()
        primary.generate.side_effect = Exception("rate limit exceeded")
        fallback = MagicMock()
        fallback.generate.return_value = LLMResponse(
            text="Gemini response",
            token_usage=TokenUsage(provider="gemini"),
            provider="gemini",
            model="models/gemini-1.5-flash",
        )
        service = LLMService(primary=primary, fallback=fallback)
        req = LLMRequest(user_prompt="hello")
        result = service.generate(req)
        assert result.text == "Gemini response"
        assert result.provider == "gemini"
        assert primary.generate.call_count == 3

    def test_generate_both_providers_fail(self) -> None:
        primary = MagicMock()
        primary.generate.side_effect = Exception("rate limit")
        fallback = MagicMock()
        fallback.generate.side_effect = Exception("gemini down")
        service = LLMService(primary=primary, fallback=fallback)
        req = LLMRequest(user_prompt="hello")
        with pytest.raises(LLMServiceError, match="Both providers failed"):
            service.generate(req)

    def test_generate_auth_error_no_fallback(self) -> None:
        primary = MagicMock()
        primary.generate.side_effect = Exception("invalid api key")
        fallback = MagicMock()
        service = LLMService(primary=primary, fallback=fallback)
        req = LLMRequest(user_prompt="hello")
        with pytest.raises(LLMProviderError, match="openai"):
            service.generate(req)
        fallback.generate.assert_not_called()

    def test_generate_with_inline_system_prompt(self) -> None:
        primary = MagicMock()
        primary.generate.return_value = LLMResponse(
            text="ok", token_usage=TokenUsage(), provider="openai", model="gpt-4o"
        )
        service = LLMService(primary=primary)
        req = LLMRequest(system_prompt="Be helpful", user_prompt="hi")
        service.generate(req)
        call_args = primary.generate.call_args
        assert call_args[0][0] == "Be helpful"

    def test_generate_with_template(self) -> None:
        PROMPT_TEMPLATES["test_tpl"] = "You are {role}. Guest: {name}"
        primary = MagicMock()
        primary.generate.return_value = LLMResponse(
            text="ok", token_usage=TokenUsage(), provider="openai", model="gpt-4o"
        )
        service = LLMService(primary=primary)
        req = LLMRequest(
            template_name="test_tpl",
            template_variables={"role": "host", "name": "Bob"},
            user_prompt="go",
        )
        service.generate(req)
        call_args = primary.generate.call_args
        assert call_args[0][0] == "You are host. Guest: Bob"

    def test_generate_template_not_found(self) -> None:
        service = LLMService(primary=MagicMock())
        req = LLMRequest(template_name="nope", user_prompt="go")
        with pytest.raises(LLMTemplateNotFoundError):
            service.generate(req)


class TestLLMServiceGenerateStream:
    def setup_method(self) -> None:
        PROMPT_TEMPLATES.clear()

    def test_stream_returns_chunks(self) -> None:
        primary = MagicMock()
        primary.generate_stream.return_value = iter(
            [
                StreamChunk(content="A"),
                StreamChunk(content="B", finished=True),
            ]
        )
        service = LLMService(primary=primary)
        req = LLMRequest(user_prompt="hi")
        chunks = list(service.generate_stream(req))
        assert len(chunks) == 2
        assert chunks[0].content == "A"
        assert chunks[1].finished is True

    def test_stream_with_template(self) -> None:
        PROMPT_TEMPLATES["stream_tpl"] = "System: {topic}"
        primary = MagicMock()
        primary.generate_stream.return_value = iter([StreamChunk(content="ok", finished=True)])
        service = LLMService(primary=primary)
        req = LLMRequest(
            template_name="stream_tpl", template_variables={"topic": "AI"}, user_prompt="go"
        )
        list(service.generate_stream(req))
        call_args = primary.generate_stream.call_args
        assert call_args[0][0] == "System: AI"

    def test_stream_template_not_found(self) -> None:
        service = LLMService(primary=MagicMock())
        req = LLMRequest(template_name="missing", user_prompt="go")
        with pytest.raises(LLMTemplateNotFoundError):
            list(service.generate_stream(req))
