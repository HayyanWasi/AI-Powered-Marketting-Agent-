from unittest.mock import MagicMock

from pydantic import BaseModel

from src.models.llm import LLMRequest, LLMResponse, TokenUsage
from src.services.llm_service import LLMService


class DummySchema(BaseModel):
    name: str


def test_groq_429_failover():
    # Test C, H
    service = LLMService()
    service._providers = {"groq": MagicMock(), "openrouter": MagicMock()}
    service._ordered_chain = MagicMock(
        return_value=[
            ("groq", service._providers["groq"], "model1"),
            ("openrouter", service._providers["openrouter"], "model2"),
        ]
    )

    class RateLimitError(Exception):
        pass

    service._providers["groq"].generate.side_effect = RateLimitError(
        "Rate limit reached. Please try again in 4.845s"
    )

    mock_resp = LLMResponse(
        text='{"name": "test"}',
        token_usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        provider="openrouter",
        model="model2",
    )
    service._providers["openrouter"].generate.return_value = mock_resp

    req = LLMRequest(user_prompt="test", json_mode=True, output_schema=DummySchema)
    resp = service.generate(req)

    assert resp.provider == "openrouter"
    service._providers["openrouter"].generate.assert_called_once()
    service._providers["groq"].generate.assert_called_once()


def test_truncation_retry():
    # Test D, E, H
    service = LLMService()
    provider_mock = MagicMock()
    service._providers = {"mock": provider_mock}
    service._ordered_chain = MagicMock(return_value=[("mock", provider_mock, "model1")])

    truncated_resp = LLMResponse(
        text='{"name": "test"',
        token_usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        provider="mock",
        model="model1",
        finish_reason="length",
    )

    success_resp = LLMResponse(
        text='{"name": "test"}',
        token_usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        provider="mock",
        model="model1",
        finish_reason="stop",
    )

    # First call returns truncated, second call returns success
    provider_mock.generate.side_effect = [truncated_resp, success_resp]

    req = LLMRequest(user_prompt="test", json_mode=True, output_schema=DummySchema)
    resp = service.generate(req)

    assert resp.finish_reason == "stop"
    assert resp.text == '{"name": "test"}'
    assert provider_mock.generate.call_count == 2

    # Verify the second call added the conciseness prompt
    second_call_args = provider_mock.generate.call_args_list[1]
    assert "Be concise" in second_call_args[0][1]  # args[1] is user_prompt
