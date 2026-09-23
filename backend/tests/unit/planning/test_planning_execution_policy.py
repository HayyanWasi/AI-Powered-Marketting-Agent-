"""Ollama planning execution policy: concurrency, timeout, and no timeout-retry.

Covers the approved policy for the single-GPU local model — a timed-out
non-streaming generation is not resent (it may still hold the GPU), while
non-timeout transient errors and remote-provider retries are preserved.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.models.llm import LLMRequest, LLMResponse, TokenUsage
from src.modules.planning.agents import panel
from src.services import llm_service
from src.services.llm_service import LLMService, _retry_with_backoff


class APITimeoutError(Exception):
    """Same class name as openai.APITimeoutError, which the classifiers key on."""


def _ok_response() -> LLMResponse:
    return LLMResponse(
        text="{}",
        token_usage=TokenUsage(0, 0, 0, "ollama"),
        provider="ollama",
        model="qwen3:8b",
        finish_reason="stop",
    )


# ── D. A timed-out Ollama request is not resent ──
def test_timeout_not_retried_when_disabled():
    calls = {"n": 0}

    def f():
        calls["n"] += 1
        raise APITimeoutError("Request timed out.")

    with patch("src.services.llm_service.time.sleep"), pytest.raises(APITimeoutError):
        _retry_with_backoff(f, retry_on_timeout=False)
    assert calls["n"] == 1  # exactly one attempt, no resend


def test_ollama_generate_does_not_retry_timeout():
    svc = LLMService()
    provider = MagicMock()
    provider.generate.side_effect = APITimeoutError("Request timed out.")
    svc._chain = [("ollama", provider, "qwen3:8b")]
    svc._rotate_providers = False

    with patch("src.services.llm_service.time.sleep"):
        with pytest.raises(llm_service.LLMServiceError):
            svc.generate(LLMRequest(user_prompt="x", timeout=180.0))
    assert provider.generate.call_count == 1


# ── E. Non-timeout transient errors and remote timeouts still retry ──
def test_non_timeout_transient_still_retried_even_when_timeout_retry_disabled():
    calls = {"n": 0}

    def transient():
        calls["n"] += 1
        raise RuntimeError("500 server error")  # transient, not a timeout

    with patch("src.services.llm_service.time.sleep"), pytest.raises(RuntimeError):
        _retry_with_backoff(transient, retry_on_timeout=False)
    assert calls["n"] == llm_service.MAX_RETRIES


def test_remote_timeout_is_retried():
    calls = {"n": 0}

    def f():
        calls["n"] += 1
        raise APITimeoutError("Request timed out.")

    with patch("src.services.llm_service.time.sleep"), pytest.raises(APITimeoutError):
        _retry_with_backoff(f, retry_on_timeout=True)
    assert calls["n"] == llm_service.MAX_RETRIES


# ── C. ask_json threads the 180s planning timeout for Ollama ──
@pytest.mark.asyncio
async def test_ask_json_threads_ollama_planning_timeout():
    captured = {}
    fake = MagicMock()
    fake.is_local_ollama.return_value = True
    fake.has_ollama_provider.return_value = True

    def _generate(request):
        captured["timeout"] = request.timeout
        return _ok_response()

    fake.generate.side_effect = _generate
    await panel.ask_json("plan_measurement", {}, llm=fake)
    assert captured["timeout"] == 180.0


@pytest.mark.asyncio
async def test_ask_json_no_forced_timeout_for_remote():
    captured = {}
    fake = MagicMock()
    fake.is_local_ollama.return_value = False
    fake.has_ollama_provider.return_value = False

    def _generate(request):
        captured["timeout"] = request.timeout
        return _ok_response()

    fake.generate.side_effect = _generate
    await panel.ask_json("plan_measurement", {}, llm=fake)
    assert captured["timeout"] is None


# ── F. All 5 specialists remain mandatory ──
def test_all_five_specialists_present():
    assert set(panel.SPECIALISTS) == {
        "audience_research",
        "positioning",
        "competitive",
        "channel_plan",
        "measurement",
    }
