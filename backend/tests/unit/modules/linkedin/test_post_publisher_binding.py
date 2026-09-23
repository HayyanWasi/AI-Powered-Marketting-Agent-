"""Publisher publishes through the post-bound LinkedIn account only.

Covers TASK 3 of the launch-binding work: the scheduled publisher must publish
each due post through ``post.linkedin_account_id`` and must never fall back to a
static/global account. A post with no bound account fails truthfully.
"""

from __future__ import annotations

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
        self.calls: list[tuple[str, str, str | None]] = []

    async def create_post(self, account_id, content, media_url=None):
        self.calls.append((account_id, content, media_url))
        return self._post_id


def _scheduled_post(account_id: str | None) -> dict:
    return {
        "id": str(uuid4()),
        "status": "scheduled",
        "linkedin_account_id": account_id,
        "full_content": "Due content",
        "scheduled_at": "2020-01-01T00:00:00+00:00",  # in the past
        "media_url": None,
    }


@pytest.mark.asyncio
async def test_publisher_uses_post_bound_account():
    post = _scheduled_post("bound-acct-1")
    store = [post]
    gateway = _FakeGateway(post_id="urn:li:activity:999")

    with (
        patch.object(post_publisher, "BaseRepository", lambda _n: _FakeRepo(_n, store)),
        patch.object(post_publisher, "get_unipile_gateway", return_value=gateway),
    ):
        summary = await post_publisher.publish_due_posts()

    assert summary["published"] == 1
    assert gateway.calls == [("bound-acct-1", "Due content", None)]
    assert post["status"] == "published"
    assert post["unipile_post_id"] == "urn:li:activity:999"
    assert post["published_at"]


@pytest.mark.asyncio
async def test_unbound_post_fails_with_no_static_fallback():
    # The publisher reads only post.linkedin_account_id and imports no global
    # account, so an unbound post can never be published through a static one.
    post = _scheduled_post(None)
    store = [post]
    gateway = _FakeGateway(post_id="urn:li:activity:should-not-happen")

    with (
        patch.object(post_publisher, "BaseRepository", lambda _n: _FakeRepo(_n, store)),
        patch.object(post_publisher, "get_unipile_gateway", return_value=gateway),
    ):
        summary = await post_publisher.publish_due_posts()

    assert summary["failed"] == 1
    assert gateway.calls == []  # never published through any account
    assert post["status"] == "failed"
