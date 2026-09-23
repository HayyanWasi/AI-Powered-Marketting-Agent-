"""LinkedIn post writing-style refinement.

Proves the targeted style change:

* generated post copy never contains an em dash (—) or en dash (–);
* those dashes are not left as sentence separators;
* genuine hyphens in compound words (real-time, well-known) are preserved;
* the plain-language / no-jargon instruction is present in the prompt;
* the existing LinkedIn structured-output contract (hook/body/cta JSON) is
  unchanged.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.models.llm import LLMResponse, TokenUsage
from src.modules.linkedin.generators.post_generator import (
    PLAIN_LANGUAGE_STYLE_RULE,
    LinkedInPostGenerator,
    _to_plain_style,
)
from src.modules.research.services.llm_router import LLMRouterService
from src.services import llm_service as llm_mod

EM_DASH = "—"
EN_DASH = "–"


def _ollama_response(text: str) -> LLMResponse:
    return LLMResponse(
        text=text,
        token_usage=TokenUsage(provider="ollama"),
        provider="ollama",
        model="qwen3:8b",
    )


# --- Deterministic sanitizer ------------------------------------------------


def test_em_and_en_dashes_removed():
    src = f"Join us{EM_DASH}it is free. Seats are limited{EN_DASH}register today."
    out = _to_plain_style(src)
    assert EM_DASH not in out
    assert EN_DASH not in out
    assert out == "Join us, it is free. Seats are limited, register today."


def test_real_hyphens_preserved():
    src = "Our real-time, well-known platform delivers state-of-the-art results."
    out = _to_plain_style(src)
    assert out == src  # ASCII hyphens are untouched


def test_dash_at_line_edges_does_not_leave_dangling_comma():
    src = f"Line one{EM_DASH}\n{EM_DASH}Line two"
    out = _to_plain_style(src)
    assert EM_DASH not in out
    assert ",\n" not in out.replace("Line one,\n", "")  # no stray line-leading comma
    assert out == "Line one,\nLine two"


def test_empty_input_is_safe():
    assert _to_plain_style("") == ""


# --- Prompt instruction -----------------------------------------------------


def test_plain_language_rule_present_and_specific():
    rule = PLAIN_LANGUAGE_STYLE_RULE.lower()
    assert "plain, natural english" in rule
    assert "em dash" in rule and "en dash" in rule
    assert "jargon" in rule
    # a couple of the named buzzwords are called out
    assert "leverage" in rule and "synergy" in rule
    # genuine compound hyphens are explicitly still allowed
    assert "real-time" in rule


# --- End-to-end through the generator --------------------------------------


@pytest.mark.asyncio
async def test_generated_post_copy_has_no_em_dash(monkeypatch):
    """Model output laden with em dashes and jargon is sanitized before it
    becomes a LinkedInPost, while the JSON contract is honored."""
    jargon_json = (
        "{"
        f'"hook": "Unlock value{EM_DASH}a game-changing webinar",'
        f'"body": "Our best-in-class team{EM_DASH}real-time insights await{EN_DASH}join now.",'
        f'"cta": "Register today{EM_DASH}link below"'
        "}"
    )

    def fake_generate(
        self, system_prompt, user_prompt, max_tokens=None, json_mode=False, timeout=None
    ):
        return _ollama_response(jargon_json)

    monkeypatch.setattr(llm_mod.OllamaProvider, "generate", fake_generate)

    gen = LinkedInPostGenerator(llm_router=LLMRouterService())  # default → local Ollama
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
    # Structured-output contract intact: distinct hook/body/cta fields.
    assert post.hook and post.body and post.cta_text
    for field in (post.hook, post.body, post.cta_text, post.full_content):
        assert EM_DASH not in field
        assert EN_DASH not in field
    # Real hyphens from the compound words survived.
    assert "real-time" in post.body
    assert "game-changing" in post.hook  # hyphen kept even though it is a flagged phrase
