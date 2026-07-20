from src.models.llm import (
    LLMRequest,
    LLMResponse,
    LLMResponseData,
    StreamChunk,
    TokenUsage,
    TokenUsageData,
)


class TestTokenUsage:
    def test_default_values(self) -> None:
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.provider == ""

    def test_to_response(self) -> None:
        usage = TokenUsage(
            prompt_tokens=10, completion_tokens=20, total_tokens=30, provider="openai"
        )
        data = usage.to_response()
        assert isinstance(data, TokenUsageData)
        assert data.prompt_tokens == 10
        assert data.completion_tokens == 20
        assert data.total_tokens == 30
        assert data.provider == "openai"


class TestTokenUsageData:
    def test_pydantic_model(self) -> None:
        data = TokenUsageData(
            prompt_tokens=5, completion_tokens=15, total_tokens=20, provider="gemini"
        )
        assert data.prompt_tokens == 5
        assert data.provider == "gemini"


class TestLLMResponse:
    def test_to_response(self) -> None:
        usage = TokenUsage(
            prompt_tokens=10, completion_tokens=20, total_tokens=30, provider="openai"
        )
        resp = LLMResponse(text="hello", token_usage=usage, provider="openai", model="gpt-4o")
        data = resp.to_response()
        assert isinstance(data, LLMResponseData)
        assert data.text == "hello"
        assert data.token_usage.prompt_tokens == 10
        assert data.provider == "openai"
        assert data.model == "gpt-4o"


class TestStreamChunk:
    def test_defaults(self) -> None:
        chunk = StreamChunk(content="hi")
        assert chunk.content == "hi"
        assert chunk.finished is False

    def test_finished(self) -> None:
        chunk = StreamChunk(content="", finished=True)
        assert chunk.finished is True


class TestLLMRequest:
    def test_minimal_request(self) -> None:
        req = LLMRequest(user_prompt="hello")
        assert req.user_prompt == "hello"
        assert req.system_prompt is None
        assert req.template_name is None
        assert req.template_variables == {}

    def test_full_request(self) -> None:
        req = LLMRequest(
            system_prompt="You are helpful",
            user_prompt="hi",
            template_name="test",
            template_variables={"key": "val"},
        )
        assert req.system_prompt == "You are helpful"
        assert req.template_name == "test"
