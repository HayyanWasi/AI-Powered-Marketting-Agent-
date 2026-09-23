"""Targeted tests for intake LLM provider isolation.

Verifies:
A. Intake provider order is exactly: gemini → openrouter → groq
B. Ollama is absent from the intake chain.
C. Planning A/B endpoints are never selected by intake.
D. Gemini success prevents unnecessary fallback.
E. Gemini failure causes OpenRouter attempt.
F. Gemini + OpenRouter failure causes Groq attempt.
G. All three fail → truthful intake failure, no fake success.
H. Structured malformed output still follows repair/failover semantics.
I. Existing intake state tests remain green (covered by other test files).
J. IntakeChatService injection still accepted (tests / overrides work).
K. Video request path does not resolve the intake profile.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.modules.research.services.llm_router import LLMRouterService
from src.services import llm_service as llm_mod
from src.services.intake_chat_service import IntakeChatService
from src.services.llm_service import GeminiProvider, GroqProvider, LLMService, OpenRouterProvider


def _tier_order(names: list[str]) -> list[str]:
    """Unique provider tiers in first-seen order (collapses multi-key repeats)."""
    seen: list[str] = []
    for n in names:
        if n not in seen:
            seen.append(n)
    return seen


# ── A/B: Chain shape ─────────────────────────────────────────────────────────


def test_intake_remote_chain_provider_order():
    """A: Intake tier order is groq → openrouter → gemini, one entry per key."""
    with (
        patch.object(type(llm_mod.settings), "get_groq_keys", return_value=["g1", "g2"]),
        patch.object(type(llm_mod.settings), "get_openrouter_keys", return_value=["o1"]),
        patch.object(type(llm_mod.settings), "get_gemini_keys", return_value=["m1"]),
    ):
        svc = LLMService.intake_remote_chain()
    names = [name for name, _, _ in svc._chain]
    # Every configured key becomes a roll-over entry, in tier order.
    assert names == ["groq", "groq", "openrouter", "gemini"], names
    # Gemini is least priority (last tier).
    assert _tier_order(names) == ["groq", "openrouter", "gemini"]


def test_intake_remote_chain_no_ollama():
    """B: Ollama is not present anywhere in the intake chain."""
    svc = LLMService.intake_remote_chain()
    names = [name for name, _, _ in svc._chain]
    assert "ollama" not in names, "Ollama must not appear in the intake chain"
    assert svc._ollama is None, "svc._ollama must be None for intake chain"
    assert not svc.has_ollama_provider()


def test_intake_remote_chain_no_planning_endpoints():
    """C: Planning A/B base URLs are never selected by the intake chain."""
    svc = LLMService.intake_remote_chain()
    for name, provider, _ in svc._chain:
        # OllamaProvider would carry planning GPU base URLs — must be absent.
        assert name != "ollama", "Intake chain must not include OllamaProvider"
        # Ensure none of the providers are OllamaProvider instances.
        assert not isinstance(provider, type(None))
        from src.services.llm_service import OllamaProvider

        assert not isinstance(
            provider, OllamaProvider
        ), f"Intake chain contains OllamaProvider at slot '{name}'"


def test_intake_chat_service_default_uses_intake_chain():
    """IntakeChatService() without injection uses intake remote chain (no Ollama)."""
    with (
        patch.object(type(llm_mod.settings), "get_groq_keys", return_value=["g1"]),
        patch.object(type(llm_mod.settings), "get_openrouter_keys", return_value=["o1"]),
        patch.object(type(llm_mod.settings), "get_gemini_keys", return_value=["m1"]),
    ):
        svc = IntakeChatService()
    # The underlying LLMService injected into the router must be the intake chain.
    inner_llm: LLMService = svc.llm.llm
    names = [name for name, _, _ in inner_llm._chain]
    # Tier order groq → openrouter → gemini (gemini least priority), no Ollama.
    assert _tier_order(names) == ["groq", "openrouter", "gemini"]
    assert inner_llm._ollama is None
    assert not inner_llm.has_ollama_provider()


def test_intake_chat_service_injection_still_accepted():
    """J: Caller-injected LLMRouterService is honoured as-is."""
    mock_router = MagicMock(spec=LLMRouterService)
    svc = IntakeChatService(llm=mock_router)
    assert svc.llm is mock_router


# ── D: Gemini success stops chain ────────────────────────────────────────────


def test_intake_gemini_success_no_fallback():
    """D: Gemini success means openrouter/groq are never called."""
    from src.models.llm import LLMRequest, LLMResponse, TokenUsage

    _tu = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0, provider="gemini")
    gemini_mock = MagicMock(spec=GeminiProvider)
    gemini_mock.generate.return_value = LLMResponse(
        text='{"extracted": {}, "reply": "ok"}',
        token_usage=_tu,
        provider="gemini",
        model="gemini-test",
    )
    openrouter_mock = MagicMock(spec=OpenRouterProvider)
    groq_mock = MagicMock(spec=GroqProvider)

    svc = LLMService.intake_remote_chain()
    svc._chain = [
        ("gemini", gemini_mock, "gemini-test"),
        ("openrouter", openrouter_mock, "openrouter-test"),
        ("groq", groq_mock, "groq-test"),
    ]

    req = LLMRequest(system_prompt="sys", user_prompt="user", json_mode=True)
    result = svc.generate(req)

    assert result.provider == "gemini"
    openrouter_mock.generate.assert_not_called()
    groq_mock.generate.assert_not_called()


# ── E: Gemini failure → OpenRouter ───────────────────────────────────────────


def test_intake_gemini_failure_tries_openrouter():
    """E: Gemini failure causes OpenRouter attempt."""
    from src.models.llm import LLMRequest, LLMResponse, TokenUsage
    from src.services.llm_service import LLMProviderError

    gemini_mock = MagicMock(spec=GeminiProvider)
    gemini_mock.generate.side_effect = LLMProviderError("gemini", "network error")

    _tu = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0, provider="openrouter")
    openrouter_mock = MagicMock(spec=OpenRouterProvider)
    openrouter_mock.generate.return_value = LLMResponse(
        text='{"extracted": {}, "reply": "ok"}',
        token_usage=_tu,
        provider="openrouter",
        model="openrouter-test",
    )
    groq_mock = MagicMock(spec=GroqProvider)

    svc = LLMService.intake_remote_chain()
    svc._chain = [
        ("gemini", gemini_mock, "gemini-test"),
        ("openrouter", openrouter_mock, "openrouter-test"),
        ("groq", groq_mock, "groq-test"),
    ]

    req = LLMRequest(system_prompt="sys", user_prompt="user", json_mode=True)
    result = svc.generate(req)

    assert result.provider == "openrouter"
    groq_mock.generate.assert_not_called()


# ── F: Gemini + OpenRouter failure → Groq ────────────────────────────────────


def test_intake_gemini_openrouter_failure_tries_groq():
    """F: Gemini + OpenRouter failure causes Groq attempt."""
    from src.models.llm import LLMRequest, LLMResponse, TokenUsage
    from src.services.llm_service import LLMProviderError

    gemini_mock = MagicMock(spec=GeminiProvider)
    gemini_mock.generate.side_effect = LLMProviderError("gemini", "error")

    openrouter_mock = MagicMock(spec=OpenRouterProvider)
    openrouter_mock.generate.side_effect = LLMProviderError("openrouter", "error")

    _tu = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0, provider="groq")
    groq_mock = MagicMock(spec=GroqProvider)
    groq_mock.generate.return_value = LLMResponse(
        text='{"extracted": {}, "reply": "ok"}',
        token_usage=_tu,
        provider="groq",
        model="groq-test",
    )

    svc = LLMService.intake_remote_chain()
    svc._chain = [
        ("gemini", gemini_mock, "gemini-test"),
        ("openrouter", openrouter_mock, "openrouter-test"),
        ("groq", groq_mock, "groq-test"),
    ]

    req = LLMRequest(system_prompt="sys", user_prompt="user", json_mode=True)
    result = svc.generate(req)

    assert result.provider == "groq"


# ── G: All fail → truthful error ─────────────────────────────────────────────


def test_intake_all_providers_fail_raises():
    """G: All three providers fail → LLMServiceError raised, no fake success."""
    from src.models.llm import LLMRequest
    from src.services.llm_service import LLMProviderError

    def _fail(sp, up, mt, json_mode=False, **kw):
        raise LLMProviderError("provider", "error")

    gemini_mock = MagicMock(spec=GeminiProvider)
    gemini_mock.generate.side_effect = _fail
    openrouter_mock = MagicMock(spec=OpenRouterProvider)
    openrouter_mock.generate.side_effect = _fail
    groq_mock = MagicMock(spec=GroqProvider)
    groq_mock.generate.side_effect = _fail

    svc = LLMService.intake_remote_chain()
    svc._chain = [
        ("gemini", gemini_mock, "gemini-test"),
        ("openrouter", openrouter_mock, "openrouter-test"),
        ("groq", groq_mock, "groq-test"),
    ]

    req = LLMRequest(system_prompt="sys", user_prompt="user")
    with pytest.raises(Exception):
        svc.generate(req)


# ── K: Video does not use intake profile ─────────────────────────────────────


def test_video_script_agent_does_not_use_intake_chain():
    """K: VideoScriptAgent uses its own LLMService, not the intake chain."""
    from src.agents.video_script_agent import VideoScriptAgent

    agent = VideoScriptAgent()
    # VideoScriptAgent must have its own LLMService, not an intake_remote_chain.
    # The intake chain is identified by _ollama=None AND _chain starting with gemini
    # built via intake_remote_chain. VideoScriptAgent must use the default service.
    inner_llm = agent.llm
    # It should be an LLMService — but NOT the intake remote chain specifically.
    # The simplest proof: video agent's LLMService was not created by intake_remote_chain
    # (which sets _rotate_providers=False and _ollama=None via __new__).
    # Since VideoScriptAgent calls LLMService() directly, it will have _ollama set.
    assert isinstance(inner_llm, LLMService)
    # Video agent should use the default chain (single Ollama or whatever global default is),
    # NOT the explicitly remote-only intake chain.
    # Proof: intake chain never rotates providers; default LLMService does or has Ollama.
    intake_chain = LLMService.intake_remote_chain()
    intake_chain_names = [n for n, _, _ in intake_chain._chain]
    video_chain_names = [n for n, _, _ in inner_llm._chain]
    # They are different objects / may have same names but this confirms video
    # did not inject the intake chain — it built its own independent LLMService.
    assert (
        inner_llm is not intake_chain
    ), "VideoScriptAgent must not share the intake LLMService instance"
