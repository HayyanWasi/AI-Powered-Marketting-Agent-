from unittest.mock import MagicMock, patch

import pytest

from src.models.llm import LLMRequest, LLMResponse, TokenUsage
from src.services.llm_service import LLMService

# All LLM traffic now routes to a single OpenAI-compatible endpoint
# (LLM_BASE_URL); the hosted multi-key providers are deliberately unwired, so
# there is no multi-credential chain left to rotate. Kept rather than deleted:
# restoring the hosted chain in LLMService.__init__ makes this test valid again.
pytestmark = pytest.mark.skip(
    reason="Hosted multi-provider chain disabled — single LLM_BASE_URL endpoint in use."
)


def test_multi_key_rotation_and_cooldown():
    # Setup test keys
    with (
        patch("src.config.settings.Settings.get_gemini_keys", return_value=["key1", "key2"]),
        patch("src.config.settings.Settings.get_openrouter_keys", return_value=["or1"]),
        patch("src.config.settings.Settings.get_groq_keys", return_value=["groq1"]),
    ):

        service = LLMService()

        # We should have 4 providers in the chain
        assert len(service._chain) == 4
        assert "gemini credential 1/2" in service._chain[0][0]
        assert "gemini credential 2/2" in service._chain[1][0]

        # Mock them
        mock_p1 = MagicMock()
        mock_p2 = MagicMock()
        mock_or = MagicMock()

        service._chain[0] = (service._chain[0][0], mock_p1, service._chain[0][2])
        service._chain[1] = (service._chain[1][0], mock_p2, service._chain[1][2])
        service._chain[2] = (service._chain[2][0], mock_or, service._chain[2][2])

        class RateLimitError(Exception):
            pass

        # p1 fails, p2 succeeds
        mock_p1.generate.side_effect = RateLimitError("Rate limit exceeded")
        mock_p2.generate.return_value = LLMResponse(
            text="Success from key 2",
            token_usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
            provider="gemini",
            model="gemini-model",
        )

        req = LLMRequest(user_prompt="test")
        resp = service.generate(req)

        assert resp.text == "Success from key 2"
        mock_p1.generate.assert_called_once()
        mock_p2.generate.assert_called_once()
        mock_or.generate.assert_not_called()

        # p1 should now be in cooldown, so next request should go straight to p2
        mock_p2.generate.reset_mock()

        # Wait, if p2 succeeded, it is NOT in cooldown. But LLMService iterates available providers.
        # It should try p1 (which is in cooldown, so it skips), then try p2.
        resp2 = service.generate(req)
        assert resp2.text == "Success from key 2"
        mock_p2.generate.assert_called_once()
