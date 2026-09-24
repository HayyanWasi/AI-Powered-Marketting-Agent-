"""Duplicate-publish protection: atomic claim of scheduled LinkedIn posts.

A scheduled post must be claimable by exactly one worker/process. Covers:
- two workers racing the same post -> exactly one provider publish call
- an already-'publishing' post is skipped
- a 'published' post is never selected again
- a failed publish does not produce a duplicate on the next run
- the startup job and interval job cannot both publish the same row
- the atomic claim leaves the bound account untouched
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
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
        return all(str(r.get(f)) <= v for f, v in self._lte.items())

    def execute(self):
        rows = [r for r in self.store if self._match(r)]
        if self._op == "update":
            # Emulate a single atomic UPDATE ... WHERE (row-level, all-or-nothing).
            for r in rows:
                r.update(self._payload or {})
        return SimpleNamespace(data=list(rows))


class _FakeRepo:
    def __init__(self, _name: str, store: list[dict]) -> None:
        self.store = store
        self.client = self

    def table(self, _name: str) -> _FakeTable:
        return _FakeTable(self.store)


class _FakeGateway:
    def __init__(self, *, post_id: str | None) -> None:
        self._post_id = post_id
        self.calls: list[str] = []

    async def create_post(self, account_id, content, media_url=None):
        # Yield control so a racing worker can attempt its own claim first.
        await asyncio.sleep(0)
        self.calls.append(account_id)
        return self._post_id


def _post(status: str = "scheduled", account: str | None = "acct-1") -> dict:
    return {
        "id": str(uuid4()),
        "status": status,
        "linkedin_account_id": account,
        "full_content": "Due content",
        "scheduled_at": "2020-01-01T00:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_two_workers_race_same_post_exactly_one_publish():
    post = _post()
    store = [post]
    gateway = _FakeGateway(post_id="urn:li:activity:1")

    with (
        patch.object(post_publisher, "BaseRepository", lambda _n: _FakeRepo(_n, store)),
        patch.object(post_publisher, "get_unipile_gateway", return_value=gateway),
    ):
        results = await asyncio.gather(
            post_publisher.publish_due_posts(),
            post_publisher.publish_due_posts(),
        )

    # Exactly one provider publish call across both workers (no duplicate).
    assert gateway.calls == ["acct-1"]
    total_published = sum(r["published"] for r in results)
    assert total_published == 1
    assert post["status"] == "published"
    # The loser either lost the claim or found nothing due — never a 2nd publish.
    total_publish_attempts = sum(r["published"] + r["failed"] for r in results)
    assert total_publish_attempts == 1
    # Account binding untouched by the claim.
    assert post["linkedin_account_id"] == "acct-1"


@pytest.mark.asyncio
async def test_claim_is_atomic_exactly_one_winner():
    """Directly: two claims of the same scheduled post yield one winner."""
    post = _post()
    store = [post]
    repo = _FakeRepo("linkedin_posts", store)

    first = post_publisher._claim_post(repo, post["id"])
    second = post_publisher._claim_post(repo, post["id"])

    assert first is True
    assert second is False  # already 'publishing' — guarded update matched nothing
    assert post["status"] == "publishing"
    assert post["linkedin_account_id"] == "acct-1"  # binding untouched


@pytest.mark.asyncio
async def test_already_publishing_post_is_skipped():
    post = _post(status="publishing")
    post["publishing_started_at"] = datetime.now(UTC).isoformat()
    store = [post]
    gateway = _FakeGateway(post_id="urn:li:activity:2")

    with (
        patch.object(post_publisher, "BaseRepository", lambda _n: _FakeRepo(_n, store)),
        patch.object(post_publisher, "get_unipile_gateway", return_value=gateway),
    ):
        summary = await post_publisher.publish_due_posts()

    assert gateway.calls == []  # not re-dispatched
    assert summary["published"] == 0
    assert post["status"] == "publishing"


@pytest.mark.asyncio
async def test_published_post_is_never_selected_again():
    post = _post(status="published")
    store = [post]
    gateway = _FakeGateway(post_id="urn:li:activity:3")

    with (
        patch.object(post_publisher, "BaseRepository", lambda _n: _FakeRepo(_n, store)),
        patch.object(post_publisher, "get_unipile_gateway", return_value=gateway),
    ):
        summary = await post_publisher.publish_due_posts()

    assert gateway.calls == []
    assert summary == {"published": 0, "failed": 0, "skipped": 0}


@pytest.mark.asyncio
async def test_failure_does_not_duplicate_on_next_run():
    post = _post()
    store = [post]
    gateway = _FakeGateway(post_id=None)  # provider failure

    with (
        patch.object(post_publisher, "BaseRepository", lambda _n: _FakeRepo(_n, store)),
        patch.object(post_publisher, "get_unipile_gateway", return_value=gateway),
    ):
        first = await post_publisher.publish_due_posts()
        second = await post_publisher.publish_due_posts()

    assert first["failed"] == 1
    assert post["status"] == "failed"
    # The failed post is not scheduled anymore, so the next run does nothing:
    # no second publish attempt, no duplicate.
    assert gateway.calls == ["acct-1"]
    assert second == {"published": 0, "failed": 0, "skipped": 0}
