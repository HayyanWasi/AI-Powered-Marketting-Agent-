"""LinkedIn per-slot strategy enforcement (duplicate-content fix).

Proves the targeted prompt-contract change:

* every post prompt carries its own Slot Theme and Messaging Pillar;
* those slot fields live in the MANDATORY prompt body (a dedicated
  "SLOT STRATEGY (MANDATORY CONTENT DIRECTIVE)" section), not only in the
  optional/truncatable strategy context;
* the directive semantics ("mandatory content directives, not optional
  context", "do NOT write a generic summary of the overall campaign",
  meaningfully different ideas per slot) are present;
* three slots with different strategies yield meaningfully different hooks
  and message angles when the model honors the directive;
* shared campaign facts (company name, CTA URL) stay consistent across posts.

No live network: the router's ``generate_json`` is stubbed to echo the slot
strategy it receives, so differentiated inputs must produce differentiated
outputs through the real prompt-building pipeline.
"""

from __future__ import annotations

import re
from uuid import uuid4

import pytest

from src.models.brand_context import BrandContext
from src.modules.linkedin.generators.post_generator import LinkedInPostGenerator
from src.modules.linkedin.models import ContentContext
from src.modules.research.services.llm_router import LLMRouterService

COMPANY_NAME = "Acme Corp"
CTA_URL = "https://acme.example/start"

SLOT_STRATEGY_HEADING = "### SLOT STRATEGY (MANDATORY CONTENT DIRECTIVE)"


def _brand() -> BrandContext:
    return BrandContext(company_profile_id=uuid4(), company_name=COMPANY_NAME)


def _ctx(
    slot_id: str, theme: str, pillar: str, *, cta: str = "", angle: str = ""
) -> ContentContext:
    """A ContentContext with shared campaign facts but slot-specific strategy."""
    return ContentContext(
        slot_id=slot_id,
        slot_date="2026-09-10",
        theme=theme,
        messaging_pillar=pillar,
        cta=cta or "Learn more",
        differentiation_angle=angle,
        brand=_brand(),
        campaign_type="product_launch",
        campaign_name="Acme Launch",
        objective="Drive signups",
        value_proposition="Faster work for busy teams",
        target_audience="Busy teams",
        cta_url=CTA_URL,
    )


THREE_SLOTS = [
    _ctx("s1", "Time savings for busy teams", "Efficiency", cta="Book a demo"),
    _ctx("s2", "Security and compliance you can trust", "Trust", cta="Read the whitepaper"),
    _ctx("s3", "Real customer success stories", "Social proof", cta="See case studies"),
]


def _build_prompt(ctx: ContentContext) -> str:
    return LinkedInPostGenerator._build_user_prompt(ctx, "### INSTRUCTIONS\nWrite a post.")


# --- Validation 1 & 2: slot fields present AND mandatory --------------------


def test_every_prompt_contains_its_slot_theme_and_pillar():
    for ctx in THREE_SLOTS:
        prompt = _build_prompt(ctx)
        assert ctx.theme in prompt
        assert ctx.messaging_pillar in prompt


def test_slot_strategy_is_in_mandatory_section_not_optional_context():
    ctx = THREE_SLOTS[0]
    prompt = _build_prompt(ctx)

    assert SLOT_STRATEGY_HEADING in prompt

    # The theme/pillar must appear inside the mandatory slot-strategy block,
    # which sits before the optional "### CAMPAIGN STRATEGY" section.
    mandatory_start = prompt.index(SLOT_STRATEGY_HEADING)
    optional_start = prompt.index("### CAMPAIGN STRATEGY")
    assert mandatory_start < optional_start

    mandatory_block = prompt[mandatory_start:optional_start]
    assert f"Slot Theme: {ctx.theme}" in mandatory_block
    assert f"Messaging Pillar: {ctx.messaging_pillar}" in mandatory_block
    assert "Slot-Specific CTA: Book a demo" in mandatory_block

    # The optional strategy section must no longer restate the slot theme/pillar.
    optional_block = prompt[optional_start:]
    assert "Slot Theme:" not in optional_block
    assert "Messaging Pillar:" not in optional_block


def test_directive_semantics_are_present():
    prompt = _build_prompt(THREE_SLOTS[0]).lower()
    assert "mandatory content directives, not optional context" in prompt
    assert "do not write a generic summary of the overall campaign" in prompt
    assert "meaningfully different ideas" in prompt
    # It must reflect the slot strategy in hook/body/message.
    assert "hook" in prompt and "message" in prompt


# --- Validation 3, 4, 5: diversity + fact preservation ---------------------


@pytest.mark.asyncio
async def test_three_slots_produce_different_hooks_with_consistent_facts(monkeypatch):
    """When the model honors the slot directive, hooks/angles differ per slot
    while shared campaign facts (company name, CTA URL) stay consistent."""

    theme_re = re.compile(r"^- Slot Theme: (.+)$", re.MULTILINE)
    pillar_re = re.compile(r"^- Messaging Pillar: (.+)$", re.MULTILINE)

    async def fake_generate_json(system_prompt, user_prompt, timeout=None, **kwargs):
        # A cooperative model: it writes strictly to the slot's own theme/pillar,
        # and always includes the canonical company name and CTA URL.
        theme = theme_re.search(user_prompt).group(1)
        pillar = pillar_re.search(user_prompt).group(1)
        return {
            "hook": f"{theme}: what {COMPANY_NAME} means for you",
            "body": f"Focused on {pillar}. {COMPANY_NAME} helps busy teams. {theme}.",
            "cta": f"Get started at {CTA_URL}",
        }

    gen = LinkedInPostGenerator(llm_router=LLMRouterService())
    monkeypatch.setattr(gen.llm, "generate_json", fake_generate_json)

    campaign_id = uuid4()
    posts = []
    for ctx in THREE_SLOTS:
        post = await gen._generate_single_post(campaign_id, ctx)
        assert post is not None
        posts.append(post)

    # Validation 3 & 4: hooks and message angles are meaningfully different.
    hooks = [p.hook for p in posts]
    assert len(set(hooks)) == len(hooks)  # all distinct
    bodies = [p.body for p in posts]
    assert len(set(bodies)) == len(bodies)
    # Each post reflects its own slot theme, not a generic campaign restatement.
    for ctx, post in zip(THREE_SLOTS, posts, strict=True):
        assert ctx.theme in post.hook
        assert ctx.messaging_pillar in post.body

    # Validation 5: shared campaign facts stay consistent across every post.
    for post in posts:
        assert COMPANY_NAME in post.body
        assert CTA_URL in post.cta_text
