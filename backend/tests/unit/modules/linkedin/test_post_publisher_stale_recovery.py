"""Fail-closed recovery for LinkedIn posts stuck in 'publishing'.

- the atomic claim stamps publishing_started_at
- a fresh 'publishing' row (under threshold) is left untouched
- a stale 'publishing' row is parked in 'needs_review'
- stale recovery never calls Unipile and never resets to 'scheduled'
- a 'needs_review' row is never selected for publishing
- a normal scheduled publish still works
- 'published' rows are unaffected by recovery
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.modules.linkedin.worker import post_publisher


class _FakeTable:
    def __init__(self, store: list[dict]) -> None:
        self.store = store
        self._filters: dict[str, str] = {}
        self._lte: dict[str, str] = {}
        self._op: str | None = None
        self._payload: dict | None = None

    def select(self, *_a, **_k):
        self._op = "select"
        return self

    def update(self, payload: dict):
        self._op = "update"
        self._payload = payload
        return self

    def eq(self, field: str, value):
        self._filters[field] = str(value)
        return self

    def lte(self, field: str, value):
        self._lte[field] = str(value)
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def _match(self, r: dict) -> bool:
        if not all(str(r.get(f)) == v for f, v in self._filters.items()):
            return False
        # NULL/None values never satisfy an lte bound (mirrors SQL).
        return all(r.get(f) is not None and str(r.get(f)) <= v for f, v in self._lte.items())

    def execute(self):
        rows = [r for r in self.store if self._match(r)]
        if self._op == "update":
            for r in rows:
                r.update(self._payload or {})
        return SimpleNamespace(data=list(rows))


class _FakeRepo:
    def __init__(self, _name: str, store: list[dict]) -> None:
        self.store = store
        self.client = self

    def table(self, _name: str) -> _FakeTable:
        return _FakeTable(self.store)


class _SpyGateway:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def create_post(self, account_id, content, media_url=None):
        self.calls.append(account_id)
        return "urn:li:activity:should-not-happen"


def _iso(minutes_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


def _row(status: str, *, started_min_ago: float | None = None) -> dict:
    return {
        "id": str(uuid4()),
        "status": status,
        "linkedin_account_id": "acct-1",
        "full_content": "content",
        "scheduled_at": "2020-01-01T00:00:00+00:00",
        "publishing_started_at": None if started_min_ago is None else _iso(started_min_ago),
    }


def test_claim_stamps_publishing_started_at():
    post = {"id": str(uuid4()), "status": "scheduled", "publishing_started_at": None}
    repo = _FakeRepo("linkedin_posts", [post])
    assert post_publisher._claim_post(repo, post["id"]) is True
    assert post["status"] == "publishing"
    assert post["publishing_started_at"] is not None


def test_fresh_publishing_row_untouched(monkeypatch):
    monkeypatch.setattr(post_publisher.settings, "linkedin_publish_stale_minutes", 15)
    fresh = _row("publishing", started_min_ago=1)  # well under threshold
    store = [fresh]
    n = post_publisher.recover_stale_publishing(_FakeRepo("linkedin_posts", store))
    assert n == 0
    assert fresh["status"] == "publishing"


def test_stale_publishing_row_parked_in_needs_review(monkeypatch):
    monkeypatch.setattr(post_publisher.settings, "linkedin_publish_stale_minutes", 15)
    stale = _row("publishing", started_min_ago=20)
    store = [stale]
    n = post_publisher.recover_stale_publishing(_FakeRepo("linkedin_posts", store))
    assert n == 1
    assert stale["status"] == "needs_review"


def test_stale_recovery_never_calls_unipile_or_resets(monkeypatch):
    monkeypatch.setattr(post_publisher.settings, "linkedin_publish_stale_minutes", 15)
    # Any attempt to obtain the gateway during recovery is a bug.
    monkeypatch.setattr(
        post_publisher,
        "get_unipile_gateway",
        lambda: (_ for _ in ()).throw(AssertionError("recovery must not touch Unipile")),
    )
    stale = _row("publishing", started_min_ago=30)
    store = [stale]
    post_publisher.recover_stale_publishing(_FakeRepo("linkedin_posts", store))
    assert stale["status"] == "needs_review"
    assert stale["status"] != "scheduled"  # never publishing -> scheduled


def test_published_rows_unaffected_by_recovery(monkeypatch):
    monkeypatch.setattr(post_publisher.settings, "linkedin_publish_stale_minutes", 15)
    pub = _row("published", started_min_ago=120)
    store = [pub]
    n = post_publisher.recover_stale_publishing(_FakeRepo("linkedin_posts", store))
    assert n == 0
    assert pub["status"] == "published"


@pytest.mark.asyncio
async def test_needs_review_never_selected_for_publishing(monkeypatch):
    monkeypatch.setattr(post_publisher.settings, "linkedin_publish_stale_minutes", 15)
    nr = _row("needs_review", started_min_ago=60)
    store = [nr]
    gw = _SpyGateway()
    with (
        patch.object(post_publisher, "BaseRepository", lambda _n: _FakeRepo(_n, store)),
        patch.object(post_publisher, "get_unipile_gateway", return_value=gw),
    ):
        summary = await post_publisher.publish_due_posts()
    assert gw.calls == []
    assert summary == {"published": 0, "failed": 0, "skipped": 0}
    assert nr["status"] == "needs_review"


@pytest.mark.asyncio
async def test_normal_scheduled_publish_still_works(monkeypatch):
    monkeypatch.setattr(post_publisher.settings, "linkedin_publish_stale_minutes", 15)
    post = _row("scheduled")
    store = [post]
    gw = _SpyGateway()

    class _OkGateway:
        def __init__(self):
            self.calls = []

        async def create_post(self, account_id, content, media_url=None):
            self.calls.append(account_id)
            return "urn:li:activity:123"

    ok = _OkGateway()
    with (
        patch.object(post_publisher, "BaseRepository", lambda _n: _FakeRepo(_n, store)),
        patch.object(post_publisher, "get_unipile_gateway", return_value=ok),
    ):
        summary = await post_publisher.publish_due_posts()
    assert summary["published"] == 1
    assert ok.calls == ["acct-1"]
    assert post["status"] == "published"
    assert post["publishing_started_at"] is not None  # claim stamped it
