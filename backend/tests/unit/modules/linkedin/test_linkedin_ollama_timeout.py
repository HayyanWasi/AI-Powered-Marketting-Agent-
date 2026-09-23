"""LinkedIn-only local-Ollama timeout override (120s), global stays 60s.

Proves a LinkedIn local-Ollama generation call receives the 120s per-request
timeout on the Ollama leg, while a non-LinkedIn call (no timeout) falls back to
the provider's default 60s client timeout — leaving global/planning/intake/video
timeouts untouched.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.models.llm import LLMResponse, TokenUsage
from src.modules.linkedin.generators.local_llm_gate import (
    LINKEDIN_LOCAL_OLLAMA_TIMEOUT_SECONDS,
)
from src.modules.linkedin.generators.post_generator import LinkedInPostGenerator
from src.modules.research.services.llm_router import LLMRouterService
from src.services import llm_service as llm_mod


def _ollama_response(text: str) -> LLMResponse:
    return LLMResponse(
        text=text,
        token_usage=TokenUsage(provider="ollama"),
        provider="ollama",
        model="qwen3:8b",
    )


def test_linkedin_timeout_constant_is_120():
    assert LINKEDIN_LOCAL_OLLAMA_TIMEOUT_SECONDS == 120.0


def test_global_provider_timeout_unchanged():
    assert llm_mod.PROVIDER_TIMEOUT_SECONDS == 60.0


@pytest.mark.asyncio
async def test_linkedin_post_generation_uses_120s_on_local_ollama(monkeypatch):
    captured: dict = {}

    def fake_generate(
        self, system_prompt, user_prompt, max_tokens=None, json_mode=False, timeout=None
    ):
        captured["timeout"] = timeout
        return _ollama_response('{"hook": "H", "body": "B", "cta": "C"}')

    monkeypatch.setattr(llm_mod.OllamaProvider, "generate", fake_generate)

    gen = LinkedInPostGenerator(llm_router=LLMRouterService())  # default → single local Ollama
    gen._build_user_prompt = lambda ctx, instr: "prompt"  # type: ignore[method-assign]
    ctx = SimpleNamespace(
        brand=SimpleNamespace(),
        slot_id="s1",
        researched_facts=(),
        event_name="",
        guest_name=None,
    )

    post = await gen._generate_single_post(uuid4(), ctx)

    assert post is not None
    assert captured["timeout"] == 120.0  # LinkedIn local-Ollama leg got 120s


@pytest.mark.asyncio
async def test_non_linkedin_call_keeps_default_timeout(monkeypatch):
    """A generate_json call without a timeout leaves the Ollama leg on its 60s
    client default — proving the 120s override is LinkedIn-specific, not global."""
    captured: dict = {"timeout": "unset"}

    def fake_generate(
        self, system_prompt, user_prompt, max_tokens=None, json_mode=False, timeout=None
    ):
        captured["timeout"] = timeout
        return _ollama_response('{"ok": true}')

    monkeypatch.setattr(llm_mod.OllamaProvider, "generate", fake_generate)

    router = LLMRouterService()  # default → single local Ollama
    await router.generate_json("sys", "user")  # no timeout (other features' path)

    assert captured["timeout"] is None  # falls back to the 60s client default
