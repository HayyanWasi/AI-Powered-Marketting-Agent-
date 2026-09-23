"""Video script/director generation runs on a remote-only rotating chain.

Proves the VideoScriptAgent LLM lane:

* never contains the local Ollama provider;
* tries providers gemini -> openrouter -> groq;
* rotates credentials across requests to spread TPM/rate limits;
* rolls over gemini key 1 -> gemini key 2 -> OpenRouter -> Groq on failure;
* fails truthfully (LLMServiceError) when every credential fails;
* still returns a valid structured 5-scene script (smoke test).

No live network is used: provider ``generate`` methods are stubbed. Keys are
fake and are never logged by production code.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.agents.video_script_agent import VideoScriptAgent
from src.models.brand_context import BrandContext
from src.models.llm import LLMResponse, TokenUsage
from src.models.video_generation_context import VideoGenerationContext
from src.services import llm_service as llm_mod
from src.services.llm_service import LLMRequest, LLMService, LLMServiceError

GEMINI_KEYS = ["gem-key-1", "gem-key-2"]
OPENROUTER_KEYS = ["or-key-1", "or-key-2"]
GROQ_KEYS = ["groq-key-1", "groq-key-2"]

_VALID_SCRIPT = (
    '{"scenes": ['
    '{"scene_number": 1, "narration": "Acme Corp changes how you work today.", "image_prompt": "wide cinematic shot, office, 8k"},'
    '{"scene_number": 2, "narration": "Slow tools hold your team back.", "image_prompt": "over the shoulder, frustrated worker, 8k"},'
    '{"scene_number": 3, "narration": "Acme gives you speed and clarity.", "image_prompt": "medium portrait, confident person, 8k"},'
    '{"scene_number": 4, "narration": "Your day finally feels easier.", "image_prompt": "close up hands, collaboration, 8k"},'
    '{"scene_number": 5, "narration": "Start with Acme Corp now.", "image_prompt": "dynamic closing, bright office, 8k"}'
    "]}"
)


@pytest.fixture(autouse=True)
def _fixed_credentials_and_clean_rotation():
    """Fixed fake keys per tier + reset global rotation/cooldown state."""
    with (
        patch.object(type(llm_mod.settings), "get_gemini_keys", lambda self: list(GEMINI_KEYS)),
        patch.object(
            type(llm_mod.settings), "get_openrouter_keys", lambda self: list(OPENROUTER_KEYS)
        ),
        patch.object(type(llm_mod.settings), "get_groq_keys", lambda self: list(GROQ_KEYS)),
    ):
        llm_mod._provider_rotation_index = 0
        llm_mod._provider_unavailable_until.clear()
        yield
        llm_mod._provider_rotation_index = 0
        llm_mod._provider_unavailable_until.clear()


def _ok_response(provider: str) -> LLMResponse:
    return LLMResponse(
        text=_VALID_SCRIPT,
        token_usage=TokenUsage(provider=provider),
        provider=provider,
        model="test-model",
    )


def _install_provider_stubs(monkeypatch, attempts: list[tuple[str, str]], fail_keys: set[str]):
    """Stub each remote provider's generate to record (provider, key) attempts.

    A key in ``fail_keys`` raises a rate-limit error (rolls over); any other key
    succeeds. Ollama is deliberately not stubbed — it must never be reached.
    """

    def make(provider_name):
        def _gen(self, system_prompt, user_prompt, max_tokens=None, json_mode=False, **kwargs):
            attempts.append((provider_name, self._api_key))
            if self._api_key in fail_keys:
                raise RuntimeError("429 rate limit / quota exceeded")
            return _ok_response(provider_name)

        return _gen

    monkeypatch.setattr(llm_mod.GeminiProvider, "generate", make("gemini"))
    monkeypatch.setattr(llm_mod.OpenRouterProvider, "generate", make("openrouter"))
    monkeypatch.setattr(llm_mod.GroqProvider, "generate", make("groq"))


def _request() -> LLMRequest:
    return LLMRequest(system_prompt="sys", user_prompt="user", json_mode=True)


# --- Chain shape ------------------------------------------------------------


def test_video_lane_excludes_ollama_and_orders_gemini_first():
    svc = LLMService.video_remote_lane()
    names = [name for name, _, _ in svc._chain]
    assert "ollama" not in names
    assert svc._ollama is None
    assert svc.has_ollama_provider() is False
    # gemini tier first (both keys), then openrouter, then groq.
    assert names == ["gemini", "gemini", "openrouter", "openrouter", "groq", "groq"]


def test_video_script_agent_uses_remote_lane_without_ollama():
    agent = VideoScriptAgent()
    names = [name for name, _, _ in agent.llm._chain]
    assert "ollama" not in names
    assert agent.llm.has_ollama_provider() is False
    assert agent.llm._rotate_providers is True


# --- Rotation ---------------------------------------------------------------


def test_credentials_rotate_across_requests():
    svc = LLMService.video_remote_lane()
    first_keys = []
    for _ in range(2):
        ordered = svc._ordered_chain()
        first_gemini = next(inst._api_key for name, inst, _ in ordered if name == "gemini")
        first_keys.append(first_gemini)
    # Request 1 starts with gemini key 1, request 2 starts with gemini key 2.
    assert first_keys == [GEMINI_KEYS[0], GEMINI_KEYS[1]]


# --- Fallback / roll-over ---------------------------------------------------


def test_gemini_key1_fails_rolls_to_gemini_key2(monkeypatch):
    attempts: list[tuple[str, str]] = []
    _install_provider_stubs(monkeypatch, attempts, fail_keys={GEMINI_KEYS[0]})

    svc = LLMService.video_remote_lane()
    response = svc.generate(_request())

    assert response.provider == "gemini"
    assert attempts[0] == ("gemini", GEMINI_KEYS[0])  # key 1 tried first
    assert attempts[1] == ("gemini", GEMINI_KEYS[1])  # rolled over to key 2
    assert len(attempts) == 2  # stopped once key 2 succeeded


def test_both_gemini_fail_falls_back_to_openrouter(monkeypatch):
    attempts: list[tuple[str, str]] = []
    _install_provider_stubs(monkeypatch, attempts, fail_keys=set(GEMINI_KEYS))

    svc = LLMService.video_remote_lane()
    response = svc.generate(_request())

    assert response.provider == "openrouter"
    tried = [name for name, _ in attempts]
    assert tried[:2] == ["gemini", "gemini"]  # both gemini keys attempted first
    assert tried[2] == "openrouter"  # then openrouter tier


def test_gemini_and_openrouter_fail_falls_back_to_groq(monkeypatch):
    attempts: list[tuple[str, str]] = []
    _install_provider_stubs(
        monkeypatch, attempts, fail_keys=set(GEMINI_KEYS) | set(OPENROUTER_KEYS)
    )

    svc = LLMService.video_remote_lane()
    response = svc.generate(_request())

    assert response.provider == "groq"
    tried = [name for name, _ in attempts]
    assert tried[:2] == ["gemini", "gemini"]
    assert tried[2:4] == ["openrouter", "openrouter"]
    assert tried[4] == "groq"


def test_all_credentials_fail_raises_truthful_error(monkeypatch):
    attempts: list[tuple[str, str]] = []
    _install_provider_stubs(
        monkeypatch, attempts, fail_keys=set(GEMINI_KEYS) | set(OPENROUTER_KEYS) | set(GROQ_KEYS)
    )

    svc = LLMService.video_remote_lane()
    with pytest.raises(LLMServiceError):
        svc.generate(_request())

    # Every configured credential was actually attempted before failing.
    assert len(attempts) == 6


# --- Structured 5-scene smoke test -----------------------------------------


def _smoke_context() -> VideoGenerationContext:
    brand = BrandContext(company_profile_id=uuid4(), company_name="Acme Corp")
    return VideoGenerationContext(
        campaign_id=uuid4(),
        owner_id=uuid4(),
        brand=brand,
        campaign_type="product_launch",
        campaign_name="Acme Launch",
        objective="Drive signups",
        target_audience="Busy teams",
        value_proposition="Faster work",
        cta_url="https://acme.example/start",
        plan_id=uuid4(),
        plan_version=1,
    )


def test_video_script_smoke_returns_five_scenes(monkeypatch):
    attempts: list[tuple[str, str]] = []
    _install_provider_stubs(monkeypatch, attempts, fail_keys=set())

    agent = VideoScriptAgent()
    scenes = asyncio.run(agent.generate_script(_smoke_context()))

    assert [s.scene_number for s in scenes] == [1, 2, 3, 4, 5]
    assert all(s.narration.strip() and s.image_prompt.strip() for s in scenes)
    # Served by the first remote tier (gemini), never Ollama.
    assert attempts[0][0] == "gemini"
    assert all(name != "ollama" for name, _ in attempts)
