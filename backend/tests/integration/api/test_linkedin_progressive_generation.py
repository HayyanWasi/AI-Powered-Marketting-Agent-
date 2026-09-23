"""TASK 1 — Backend post-by-post progressive delivery.

Proves the streaming generate endpoint emits post-level progress events while
preserving the existing atomic persistence semantics:

* ``generation_started`` is emitted first with the total post count.
* ``post_completed`` is emitted for each fully validated post (never partial JSON).
* ``generation_completed`` is emitted only on success and carries the canonical
  (DB-identified) posts from the single atomic RPC.
* a failure emits ``generation_failed`` and persists nothing.

A generator-level test proves ``generate_all_posts`` actually drives the
progress callbacks with finalized posts, and never for a post that failed.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.dependencies import AuthenticatedUser
from src.api.v1.linkedin import generate_campaign_content_stream
from src.models.brand_context import BrandContext
from src.modules.linkedin.generators.post_generator import LinkedInPostGenerator
from src.modules.linkedin.models import LinkedInPost, OutreachTemplate, PostStatus
from src.modules.linkedin.scheduling.models import SchedulePlan, ScheduleSlot
from src.modules.planning.models.campaign_plan import (
    CalendarSlot,
    CampaignPlan,
    ChannelPlan,
    InputIdentity,
)
from src.services.campaign_context_service import (
    compute_brand_fingerprint,
    compute_intake_fingerprint,
)


# ── Streaming response consumption ────────────────────────────────────────────


async def _collect_events(response) -> list[dict]:
    """Drain a StreamingResponse's NDJSON body into parsed event dicts."""
    lines: list[str] = []
    async for chunk in response.body_iterator:
        text = chunk.decode() if isinstance(chunk, bytes) else chunk
        lines.append(text)
    events: list[dict] = []
    for raw in "".join(lines).splitlines():
        raw = raw.strip()
        if raw:
            events.append(json.loads(raw))
    return events


# ── Shared endpoint context (two calendar slots) ──────────────────────────────


class _RpcRequest:
    def __init__(self, *, data=None, error: Exception | None = None) -> None:
        self._data = data
        self._error = error

    def execute(self):
        if self._error:
            raise self._error
        return SimpleNamespace(data=self._data)


class _Client:
    def __init__(self, *, data=None, error: Exception | None = None) -> None:
        self.data = data
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def rpc(self, name: str, args: dict) -> _RpcRequest:
        self.calls.append((name, args))
        return _RpcRequest(data=self.data, error=self.error)


def _endpoint_context():
    campaign_id = uuid4()
    user_id = uuid4()
    profile_id = uuid4()
    brand = BrandContext(
        company_profile_id=profile_id,
        company_name="Progressive Brand",
        brand_tone="Direct",
        negative_guardrails=("Never use buzzwords",),
        profile_updated_at="2026-09-17T10:00:00+00:00",
    )
    inputs = SimpleNamespace(
        brand=brand,
        intake={"updated_at": "2026-09-17T10:05:00+00:00"},
        campaign=SimpleNamespace(name="Progressive", schedule=None, goals=None, platforms=[]),
    )
    plan = CampaignPlan(
        campaign_id=campaign_id,
        input_identity=InputIdentity(
            campaign_id=campaign_id,
            company_profile_id=profile_id,
            brand_version=compute_brand_fingerprint(inputs.brand),
            intake_hash=compute_intake_fingerprint(inputs.intake, inputs.campaign),
        ),
        channel_plan=ChannelPlan(
            calendar_slots=(
                CalendarSlot(slot_id="slot-1", date="2026-09-20", platform="LinkedIn", theme="A", cta="Go"),
                CalendarSlot(slot_id="slot-2", date="2026-09-22", platform="LinkedIn", theme="B", cta="Go"),
            )
        ),
    )
    posts = [
        LinkedInPost(
            campaign_id=campaign_id,
            slot_id="slot-1",
            scheduled_at=datetime(2026, 9, 20, 10, tzinfo=UTC),
            hook="HOOK_1",
            body="BODY_1",
            cta_text="CTA_1",
            full_content="HOOK_1\n\nBODY_1\n\nCTA_1",
            status=PostStatus.DRAFT,
        ),
        LinkedInPost(
            campaign_id=campaign_id,
            slot_id="slot-2",
            scheduled_at=datetime(2026, 9, 22, 10, tzinfo=UTC),
            hook="HOOK_2",
            body="BODY_2",
            cta_text="CTA_2",
            full_content="HOOK_2\n\nBODY_2\n\nCTA_2",
            status=PostStatus.DRAFT,
        ),
    ]
    outreach = OutreachTemplate(
        campaign_id=campaign_id,
        step_invite_msg="INVITE",
        step_value_msg="VALUE",
        step_followup_msg="FOLLOWUP",
    )
    user = AuthenticatedUser(id=str(user_id), roles=["user"], permissions=[])
    return campaign_id, user, inputs, plan, posts, outreach


def _driver(posts, *, fail_after: int | None = None):
    """Build a generate_all_posts stand-in that drives the progress callbacks.

    It emits started/completed callbacks in order (like the real generator would)
    and returns the posts. ``fail_after`` raises once that many posts completed,
    mimicking a mid-batch generation failure.
    """

    async def _fake(campaign_id, plan, brief, *, on_post_started=None, on_post_completed=None, **kwargs):
        total = len(posts)
        for i, post in enumerate(posts, 1):
            if on_post_started is not None:
                await on_post_started(i, post.slot_id, total)
            if fail_after is not None and i > fail_after:
                raise RuntimeError("forced generation failure")
            if on_post_completed is not None:
                await on_post_completed(i, post.slot_id, total, post)
        return posts

    return _fake


@pytest.mark.asyncio
async def test_stream_emits_started_completed_and_persists_atomically() -> None:
    campaign_id, user, inputs, plan, posts, outreach = _endpoint_context()
    db_ids = [uuid4(), uuid4()]
    payload = {
        "posts": [
            {**posts[0].to_dict(), "id": str(db_ids[0]), "campaign_id": str(campaign_id)},
            {**posts[1].to_dict(), "id": str(db_ids[1]), "campaign_id": str(campaign_id)},
        ],
        "sequence": {"id": str(uuid4()), "campaign_id": str(campaign_id)},
    }
    client = _Client(data=payload)
    repository = SimpleNamespace(client=client)

    with (
        patch("src.api.v1.linkedin.CampaignContextResolver.resolve", new=AsyncMock(return_value=inputs)),
        patch("src.api.v1.linkedin.PlanRefinementService.get_plan", new=AsyncMock(return_value=plan)),
        patch("src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts", new=AsyncMock(side_effect=_driver(posts))),
        patch("src.api.v1.linkedin.OutreachSequenceGenerator.generate_sequence", new=AsyncMock(return_value=outreach)),
        patch("src.api.v1.linkedin.BaseRepository", return_value=repository),
    ):
        response = await generate_campaign_content_stream(campaign_id, user=user)
        events = await _collect_events(response)

    kinds = [e["event"] for e in events]
    # generation_started is first and carries the total.
    assert kinds[0] == "generation_started"
    assert events[0]["total_posts"] == 2
    # Both posts produced a post_completed carrying a complete, non-partial payload.
    completed = [e for e in events if e["event"] == "post_completed"]
    assert len(completed) == 2
    for e in completed:
        assert e["post"]["hook"] and e["post"]["body"] and e["post"]["cta_text"]
        assert e["post"]["full_content"]
        # provisional preview: no DB identity leaked before persistence
        assert "id" not in e["post"]
    # generation_completed is last and carries canonical (DB-identified) posts.
    assert kinds[-1] == "generation_completed"
    assert events[-1]["completed_count"] == 2
    assert {p["id"] for p in events[-1]["posts"]} == {str(db_ids[0]), str(db_ids[1])}

    # Persistence semantics unchanged: exactly one atomic RPC, identity stripped.
    assert len(client.calls) == 1
    assert client.calls[0][0] == "replace_linkedin_campaign_content"
    rpc_args = client.calls[0][1]
    assert rpc_args["p_campaign_id"] == str(campaign_id)
    assert rpc_args["p_user_id"] == user.id
    for p in rpc_args["p_posts"]:
        assert "id" not in p and "campaign_id" not in p and "created_at" not in p


@pytest.mark.asyncio
async def test_stream_first_post_completes_before_generation_completed() -> None:
    campaign_id, user, inputs, plan, posts, outreach = _endpoint_context()
    client = _Client(data={"posts": [{"id": str(uuid4())}], "sequence": {"id": str(uuid4())}})
    repository = SimpleNamespace(client=client)

    with (
        patch("src.api.v1.linkedin.CampaignContextResolver.resolve", new=AsyncMock(return_value=inputs)),
        patch("src.api.v1.linkedin.PlanRefinementService.get_plan", new=AsyncMock(return_value=plan)),
        patch("src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts", new=AsyncMock(side_effect=_driver(posts))),
        patch("src.api.v1.linkedin.OutreachSequenceGenerator.generate_sequence", new=AsyncMock(return_value=outreach)),
        patch("src.api.v1.linkedin.BaseRepository", return_value=repository),
    ):
        response = await generate_campaign_content_stream(campaign_id, user=user)
        events = await _collect_events(response)

    kinds = [e["event"] for e in events]
    first_completed = kinds.index("post_completed")
    generation_completed = kinds.index("generation_completed")
    assert first_completed < generation_completed


@pytest.mark.asyncio
async def test_stream_failure_emits_generation_failed_and_persists_nothing() -> None:
    campaign_id, user, inputs, plan, posts, outreach = _endpoint_context()
    client = _Client(data={})
    repository = SimpleNamespace(client=client)

    with (
        patch("src.api.v1.linkedin.CampaignContextResolver.resolve", new=AsyncMock(return_value=inputs)),
        patch("src.api.v1.linkedin.PlanRefinementService.get_plan", new=AsyncMock(return_value=plan)),
        patch(
            "src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts",
            new=AsyncMock(side_effect=_driver(posts, fail_after=1)),
        ),
        patch("src.api.v1.linkedin.OutreachSequenceGenerator.generate_sequence", new=AsyncMock(return_value=outreach)),
        patch("src.api.v1.linkedin.BaseRepository", return_value=repository),
    ):
        response = await generate_campaign_content_stream(campaign_id, user=user)
        events = await _collect_events(response)

    kinds = [e["event"] for e in events]
    assert "generation_completed" not in kinds
    assert kinds[-1] == "generation_failed"
    failed = events[-1]
    assert failed["completed_count"] == 1  # only the first post finished
    assert failed["total_posts"] == 2
    # Truthful, safe error — no stack trace / internals leaked.
    assert failed["error"] == "LinkedIn generation failed. Please retry."
    # Atomic persistence never ran → no partial campaign saved.
    assert client.calls == []


@pytest.mark.asyncio
async def test_stream_precondition_failure_returns_http_error_not_stream() -> None:
    from fastapi import HTTPException

    campaign_id = uuid4()
    user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])

    with (
        patch(
            "src.api.v1.linkedin.CampaignContextResolver.resolve",
            new=AsyncMock(side_effect=HTTPException(404, "Campaign not found or access denied.")),
        ),
        pytest.raises(HTTPException) as error,
    ):
        await generate_campaign_content_stream(campaign_id, user=user)

    assert error.value.status_code == 404


# ── TASK 3: controlled end-to-end progressive-delivery verification ───────────


@pytest.mark.asyncio
async def test_e2e_first_post_reaches_consumer_before_generation_completes() -> None:
    """The consumer must receive post 1 WHILE generation is still in progress.

    The driver emits post 1, then blocks until the streaming consumer has actually
    received that event over the wire, and only then finishes. If the endpoint
    buffered the whole response until generation ended, the driver would block
    forever — the ``wait_for`` guard would trip, generation would report failure,
    and the ``generation_completed`` assertion below would fail. Passing this test
    therefore proves genuine post-by-post progressive delivery.
    """
    campaign_id, user, inputs, plan, posts, outreach = _endpoint_context()
    client = _Client(data={"posts": [{"id": str(uuid4())}], "sequence": {"id": str(uuid4())}})
    repository = SimpleNamespace(client=client)

    consumer_saw_first = asyncio.Event()

    async def driver(campaign_id, plan, brief, *, on_post_started=None, on_post_completed=None, **kwargs):
        await on_post_started(1, posts[0].slot_id, 2)
        await on_post_completed(1, posts[0].slot_id, 2, posts[0])
        # Block until the consumer confirms it received post 1 over the stream.
        await asyncio.wait_for(consumer_saw_first.wait(), timeout=5)
        await on_post_started(2, posts[1].slot_id, 2)
        await on_post_completed(2, posts[1].slot_id, 2, posts[1])
        return posts

    observed_order: list[str] = []

    with (
        patch("src.api.v1.linkedin.CampaignContextResolver.resolve", new=AsyncMock(return_value=inputs)),
        patch("src.api.v1.linkedin.PlanRefinementService.get_plan", new=AsyncMock(return_value=plan)),
        patch("src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts", new=AsyncMock(side_effect=driver)),
        patch("src.api.v1.linkedin.OutreachSequenceGenerator.generate_sequence", new=AsyncMock(return_value=outreach)),
        patch("src.api.v1.linkedin.BaseRepository", return_value=repository),
    ):
        response = await generate_campaign_content_stream(campaign_id, user=user)
        async for chunk in response.body_iterator:
            text = chunk.decode() if isinstance(chunk, bytes) else chunk
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                observed_order.append(ev["event"])
                if ev["event"] == "post_completed" and ev.get("index") == 1:
                    # Unblock the generator only after receiving post 1 mid-flight.
                    consumer_saw_first.set()

    # Observed the full progressive sequence, terminating on success (not failure).
    assert observed_order[0] == "generation_started"
    assert "post_completed" in observed_order
    assert observed_order[-1] == "generation_completed"
    assert "generation_failed" not in observed_order
    # First post was delivered strictly before the campaign finished.
    first_post = observed_order.index("post_completed")
    completed = observed_order.index("generation_completed")
    assert first_post < completed
    # Both posts were delivered progressively.
    assert observed_order.count("post_completed") == 2


# ── Generator-level: callbacks driven by the real generate_all_posts ──────────


def _generator_plan():
    campaign_id = uuid4()
    profile_id = uuid4()
    sid1, sid2 = uuid4(), uuid4()
    schedule_plan = SchedulePlan(
        campaign_start=date(2026, 9, 20),
        campaign_end=date(2026, 9, 30),
        primary_timezone="Asia/Karachi",
        recommended_cadence="2x/week",
        cadence_reason="test",
        slots=(
            ScheduleSlot(
                slot_id=sid1,
                scheduled_at_utc=datetime(2026, 9, 20, 5, tzinfo=UTC),
                local_date=date(2026, 9, 20),
                local_time=time(10, 0),
                timezone="Asia/Karachi",
                schedule_reason="reason-1",
            ),
            ScheduleSlot(
                slot_id=sid2,
                scheduled_at_utc=datetime(2026, 9, 22, 5, tzinfo=UTC),
                local_date=date(2026, 9, 22),
                local_time=time(10, 0),
                timezone="Asia/Karachi",
                schedule_reason="reason-2",
            ),
        ),
    )
    channel_plan = ChannelPlan(
        calendar_slots=(
            CalendarSlot(slot_id=str(sid1), date="2026-09-20", platform="LinkedIn", theme="T1", cta="C1"),
            CalendarSlot(slot_id=str(sid2), date="2026-09-22", platform="LinkedIn", theme="T2", cta="C2"),
        )
    )
    plan = CampaignPlan(
        campaign_id=campaign_id,
        input_identity=InputIdentity(
            campaign_id=campaign_id,
            company_profile_id=profile_id,
            brand_version="v1",
            intake_hash="h1",
        ),
        channel_plan=channel_plan,
        schedule_plan=schedule_plan,
    )
    brand = BrandContext(
        company_profile_id=profile_id,
        company_name="Gen Brand",
        brand_tone="Direct",
        negative_guardrails=("No buzzwords",),
        profile_updated_at="2026-09-17T10:00:00+00:00",
    )
    return campaign_id, plan, brand


def _fake_build_context(slot, plan, brief, **kwargs):
    return SimpleNamespace(slot_id=slot.slot_id)


@pytest.mark.asyncio
async def test_generate_all_posts_invokes_completed_callback_with_finalized_posts() -> None:
    campaign_id, plan, brand = _generator_plan()
    started: list[tuple] = []
    completed: list[LinkedInPost] = []

    async def on_started(index, slot_id, total):
        started.append((index, slot_id, total))

    async def on_completed(index, slot_id, total, post):
        completed.append(post)

    async def fake_single(cid, ctx, scheduled_at=None):
        return LinkedInPost(
            campaign_id=cid,
            slot_id=ctx.slot_id,
            scheduled_at=scheduled_at or datetime.now(UTC),
            hook="H",
            body="B",
            cta_text="C",
            full_content="H\n\nB\n\nC",
            status=PostStatus.DRAFT,
        )

    with (
        patch(
            "src.modules.linkedin.generators.post_generator.ContentContextBuilder.build_context",
            new=MagicMock(side_effect=_fake_build_context),
        ),
        patch(
            "src.modules.linkedin.generators.post_generator.LinkedInPostGenerator._generate_single_post",
            new=AsyncMock(side_effect=fake_single),
        ),
    ):
        result = await LinkedInPostGenerator().generate_all_posts(
            campaign_id,
            plan,
            None,
            brand=brand,
            on_post_started=on_started,
            on_post_completed=on_completed,
        )

    assert len(result) == 2
    assert len(started) == 2
    assert len(completed) == 2
    # Completed posts are finalized with canonical schedule metadata.
    tz = {p.timezone for p in completed}
    reasons = {p.schedule_reason for p in completed}
    assert tz == {"Asia/Karachi"}
    assert reasons == {"reason-1", "reason-2"}


@pytest.mark.asyncio
async def test_generate_all_posts_does_not_emit_completed_for_failed_post() -> None:
    campaign_id, plan, brand = _generator_plan()
    completed: list[LinkedInPost] = []

    async def on_completed(index, slot_id, total, post):
        completed.append(post)

    async def failing_single(cid, ctx, scheduled_at=None):
        raise RuntimeError("model failed")

    with (
        patch(
            "src.modules.linkedin.generators.post_generator.ContentContextBuilder.build_context",
            new=MagicMock(side_effect=_fake_build_context),
        ),
        patch(
            "src.modules.linkedin.generators.post_generator.LinkedInPostGenerator._generate_single_post",
            new=AsyncMock(side_effect=failing_single),
        ),
        pytest.raises(Exception),
    ):
        await LinkedInPostGenerator().generate_all_posts(
            campaign_id,
            plan,
            None,
            brand=brand,
            on_post_completed=on_completed,
        )

    # A failed post is never surfaced as completed.
    assert completed == []
