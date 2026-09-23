"""Multi-key roll-over failover: groq → openrouter → gemini (gemini least).

Proves the remote chain uses ALL configured API keys as roll-over fallbacks, a
rate-limited key rolls over to its sibling key of the same provider (per-credential
cooldown), and Gemini is only reached as the last resort.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.models.llm import LLMRequest, LLMResponse, TokenUsage
from src.services import llm_service as llm_mod
from src.services.llm_service import LLMService, _build_credential_chain


@pytest.fixture(autouse=True)
def _reset_rotation_state():
    llm_mod._provider_rotation_index = 0
    llm_mod._provider_unavailable_until.clear()
    yield
    llm_mod._provider_unavailable_until.clear()


def _ok(provider: str) -> MagicMock:
    m = MagicMock()
    m.generate.return_value = LLMResponse(
        text="ok",
        token_usage=TokenUsage(provider=provider),
        provider=provider,
        model="m",
    )
    return m


def test_build_credential_chain_uses_all_keys_in_tier_order():
    with (
        patch.object(type(llm_mod.settings), "get_groq_keys", return_value=["g1", "g2"]),
        patch.object(type(llm_mod.settings), "get_openrouter_keys", return_value=["o1", "o2", "o3"]),
        patch.object(type(llm_mod.settings), "get_gemini_keys", return_value=["m1", "m2", "m3"]),
    ):
        chain = _build_credential_chain(["groq", "openrouter", "gemini"])
    names = [n for n, _, _ in chain]
    assert names == [
        "groq", "groq",
        "openrouter", "openrouter", "openrouter",
        "gemini", "gemini", "gemini",
    ]
    # Every key is its own distinct provider instance (roll-over target).
    assert len({id(p) for _, p, _ in chain}) == 8


def test_empty_tier_is_skipped():
    with (
        patch.object(type(llm_mod.settings), "get_groq_keys", return_value=["g1"]),
        patch.object(type(llm_mod.settings), "get_openrouter_keys", return_value=[]),
        patch.object(type(llm_mod.settings), "get_gemini_keys", return_value=["m1"]),
    ):
        chain = _build_credential_chain(["groq", "openrouter", "gemini"])
    assert [n for n, _, _ in chain] == ["groq", "gemini"]


def test_rate_limited_key_rolls_over_to_sibling_key():
    with (
        patch.object(type(llm_mod.settings), "get_groq_keys", return_value=["g1", "g2"]),
        patch.object(type(llm_mod.settings), "get_openrouter_keys", return_value=["o1"]),
        patch.object(type(llm_mod.settings), "get_gemini_keys", return_value=["m1"]),
    ):
        svc = LLMService.intake_remote_chain()

    g1, g2, o1, m1 = MagicMock(), _ok("groq"), MagicMock(), MagicMock()
    g1.generate.side_effect = Exception("429 rate limit exceeded")
    svc._chain = [("groq", g1, "m"), ("groq", g2, "m"), ("openrouter", o1, "m"), ("gemini", m1, "m")]

    res = svc.generate(LLMRequest(user_prompt="x"))

    assert res.provider == "groq"
    g1.generate.assert_called_once()   # rate-limited key tried
    g2.generate.assert_called_once()   # rolled over to sibling groq key
    o1.generate.assert_not_called()    # never dropped to lower tier
    m1.generate.assert_not_called()    # gemini (least priority) untouched


def test_gemini_is_last_resort_when_groq_and_openrouter_fail():
    with (
        patch.object(type(llm_mod.settings), "get_groq_keys", return_value=["g1"]),
        patch.object(type(llm_mod.settings), "get_openrouter_keys", return_value=["o1"]),
        patch.object(type(llm_mod.settings), "get_gemini_keys", return_value=["m1"]),
    ):
        svc = LLMService.intake_remote_chain()

    g1, o1, m1 = MagicMock(), MagicMock(), _ok("gemini")
    g1.generate.side_effect = Exception("groq down")
    o1.generate.side_effect = Exception("openrouter down")
    svc._chain = [("groq", g1, "m"), ("openrouter", o1, "m"), ("gemini", m1, "m")]

    res = svc.generate(LLMRequest(user_prompt="x"))

    assert res.provider == "gemini"  # reached only after groq + openrouter failed
    g1.generate.assert_called_once()
    o1.generate.assert_called_once()
    m1.generate.assert_called_once()
