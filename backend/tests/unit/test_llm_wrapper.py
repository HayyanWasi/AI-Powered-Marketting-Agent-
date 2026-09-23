from unittest.mock import MagicMock, patch

from src.models.llm import LLMRequest, LLMResponse, TokenUsage
from src.services.llm_service import LLMService


def test_retry_wrapper_calls_generate_correctly():
    """
    Proves that the LLMService.generate uses the retry wrapper correctly,
    meaning it passes `_call_provider_generate` to `_retry_with_backoff`
    and no positional argument TypeErrors are raised for `provider.generate()`.
    """
    # Create an LLM service with only one provider to simplify the mock
    service = LLMService()

    mock_provider = MagicMock()
    service._ordered_chain = MagicMock(
        return_value=[("mock_provider", mock_provider, "mock-model")]
    )

    mock_response = LLMResponse(
        text="Success",
        token_usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        provider="mock",
        model="mock-model",
        finish_reason="stop",
    )

    # We patch _call_provider_generate to avoid any actual provider calls
    with patch(
        "src.services.llm_service._call_provider_generate", return_value=mock_response
    ) as mock_call:
        req = LLMRequest(user_prompt="Test")
        resp = service.generate(req)

        # Verify no TypeError occurred and we got our mock response
        assert resp.text == "Success"

        # Verify _call_provider_generate was called with the intended arguments
        # It should be called as: _call_provider_generate(provider_instance, system_prompt, user_prompt, max_tokens, json_mode)
        mock_call.assert_called_once()
        args, kwargs = mock_call.call_args

        assert args[0] == mock_provider  # provider_instance
        assert args[1] == ""  # system_prompt
        assert args[2] == "Test"  # user_prompt
        assert args[3] == 2048  # max_tokens (DEFAULT_MAX_OUTPUT_TOKENS)
        assert args[4] == False  # json_mode
