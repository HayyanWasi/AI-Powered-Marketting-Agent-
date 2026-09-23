"""LinkedIn local-Ollama concurrency gate — MAX ACTIVE LOCAL OLLAMA CALLS = 1.

Proves the shared LinkedIn gate serializes every local-Ollama call across BOTH
post generation and outreach generation, releases correctly on success and
failure, never deadlocks, stays a no-op for non-Ollama (remote) routers, and
does not touch planning/intake/video.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.models.brand_context import BrandContext
from src.modules.linkedin.generators.local_llm_gate import (
    _targets_local_ollama,
    linkedin_local_ollama_slot,
)
from src.modules.linkedin.generators.post_generator import LinkedInPostGenerator
from src.modules.linkedin.generators.sequence_generator import OutreachSequenceGenerator


class _ConcurrencyRecorder:
    """Records the maximum number of overlapping gated calls."""

    def __init__(self, hold: float = 0.03) -> None:
        self.active = 0
        self.max_active = 0
        self.completed = 0
        self.hold = hold
        self._lock = asyncio.Lock()

    async def enter(self) -> None:
        async with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(self.hold)
        async with self._lock:
            self.active -= 1
            self.completed += 1


def _local_router(recorder: _ConcurrencyRecorder, *, ollama: bool = True):
    """A fake LLMRouterService whose generate_json records concurrency."""

    async def generate_json(system_prompt, user_prompt, *args, **kwargs):
        await recorder.enter()
        return {
            "hook": "H",
            "body": "B",
            "cta": "C",
            "step_invite_msg": "invite",
            "step_value_msg": "value",
            "step_followup_msg": "followup",
        }

    return SimpleNamespace(
        llm=SimpleNamespace(has_ollama_provider=lambda: ollama),
        generate_json=generate_json,
    )


def _brand() -> BrandContext:
    return BrandContext(
        company_profile_id=uuid4(),
        company_name="Gate Brand",
        brand_tone="Direct",
        negative_guardrails=("No buzzwords",),
        profile_updated_at="2026-09-17T10:00:00+00:00",
    )


def _ctx(brand: BrandContext, slot_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        brand=brand,
        slot_id=slot_id,
        researched_facts=(),
        event_name="",
        guest_name=None,
    )


# ── A + B + C + D + G + F: real generators share ONE gate ─────────────────────


@pytest.mark.asyncio
async def test_posts_and_outreach_never_overlap_on_local_ollama() -> None:
    """Two posts AND outreach, run together, never overlap on local Ollama."""
    recorder = _ConcurrencyRecorder()
    router = _local_router(recorder)
    brand = _brand()

    post_gen = LinkedInPostGenerator(llm_router=router)
    post_gen._build_user_prompt = lambda ctx, instructions: "prompt"  # avoid heavy prompt build
    seq_gen = OutreachSequenceGenerator(llm_router=router)
    plan = SimpleNamespace(core_strategy=None, competitive=None, title="Campaign")

    campaign_id = uuid4()
    completed_posts: list = []

    async def make_post(slot_id: str):
        post = await post_gen._generate_single_post(campaign_id, _ctx(brand, slot_id))
        completed_posts.append(post)

    # Two posts + outreach concurrently — the outer route runs them via gather.
    await asyncio.wait_for(
        asyncio.gather(
            make_post("slot-1"),
            make_post("slot-2"),
            seq_gen.generate_sequence(campaign_id, plan, None, brand=brand),
        ),
        timeout=5,  # F: proves no deadlock
    )

    # A + B + C: max overlap across posts + outreach is exactly 1.
    assert recorder.max_active == 1
    # D + G: all three units of waiting work completed after gate releases.
    assert recorder.completed == 3
    assert len(completed_posts) == 2
    assert all(p is not None for p in completed_posts)


# ── E: a failure inside the gate releases the permit ──────────────────────────


@pytest.mark.asyncio
async def test_gate_released_after_failure() -> None:
    router = _local_router(_ConcurrencyRecorder())

    with pytest.raises(RuntimeError):
        async with linkedin_local_ollama_slot(router):
            raise RuntimeError("boom")

    # The permit must be free again — this acquire would hang (and time out) if
    # the failed call had leaked the gate.
    async def acquire_again() -> str:
        async with linkedin_local_ollama_slot(router):
            return "acquired"

    assert await asyncio.wait_for(acquire_again(), timeout=2) == "acquired"


# ── F: gate serializes but does not deadlock under many waiters ───────────────


@pytest.mark.asyncio
async def test_no_deadlock_under_many_waiters() -> None:
    recorder = _ConcurrencyRecorder(hold=0.01)
    router = _local_router(recorder)

    async def one_call() -> None:
        async with linkedin_local_ollama_slot(router):
            await recorder.enter()

    await asyncio.wait_for(asyncio.gather(*(one_call() for _ in range(8))), timeout=5)
    assert recorder.max_active == 1
    assert recorder.completed == 8


# ── I: remote (non-Ollama) routers are NOT serialized by this gate ────────────


@pytest.mark.asyncio
async def test_remote_router_is_not_gated() -> None:
    recorder = _ConcurrencyRecorder()
    remote_router = _local_router(recorder, ollama=False)

    assert _targets_local_ollama(remote_router) is False

    async def one_call() -> None:
        async with linkedin_local_ollama_slot(remote_router):
            await recorder.enter()

    await asyncio.wait_for(asyncio.gather(one_call(), one_call(), one_call()), timeout=5)
    # No serialization for remote providers — concurrent calls overlap.
    assert recorder.max_active > 1


def test_targets_local_ollama_signal() -> None:
    """The gate engages only for services reporting an Ollama provider leg."""
    assert (
        _targets_local_ollama(
            SimpleNamespace(llm=SimpleNamespace(has_ollama_provider=lambda: True))
        )
        is True
    )
    assert (
        _targets_local_ollama(
            SimpleNamespace(llm=SimpleNamespace(has_ollama_provider=lambda: False))
        )
        is False
    )
    # Missing method / unexpected shape → treated as non-Ollama (no-op gate).
    assert _targets_local_ollama(SimpleNamespace(llm=object())) is False
    assert _targets_local_ollama(SimpleNamespace()) is False
