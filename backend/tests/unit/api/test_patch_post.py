"""Phase B regression: PATCH post editor ownership, status locks, char limit.

Recreated as an adjacent regression for Phase D. Uses in-process TestClient +
fake Supabase; no network, no LLM.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.main import app

USER_A = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
CAMPAIGN_ID = str(uuid4())


class _FakeTable:
    def __init__(self, store):
        self.store = store
        self._f = {}
        self._op = None
        self._payload = None

    def select(self, *_a, **_k):
        self._op = "select"
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def eq(self, f, v):
        self._f[f] = str(v)
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        rows = [r for r in self.store if all(str(r.get(k)) == v for k, v in self._f.items())]
        if self._op == "update":
            for r in rows:
                r.update(self._payload or {})
        return SimpleNamespace(data=list(rows))


class _FakeRepo:
    def __init__(self, name, stores):
        self.table_name = name
        self.stores = stores
        self.client = self

    def table(self, name):
        return _FakeTable(self.stores.setdefault(name, []))


class _FakeCampaignService:
    def __init__(self, owner):
        self._owner = owner

    async def get_campaign(self, campaign_id, user_id, *_a, **_k):
        if str(user_id) != self._owner:
            raise HTTPException(status_code=404, detail="not found")
        return SimpleNamespace(id=str(campaign_id))


@pytest.fixture(autouse=True)
def _clean():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_authenticated_user] = lambda: USER_A
    yield
    patch.stopall()
    app.dependency_overrides.clear()


def _post(status="draft"):
    return {
        "id": str(uuid4()),
        "campaign_id": CAMPAIGN_ID,
        "status": status,
        "hook": "H",
        "body": "B",
        "cta_text": "C",
        "full_content": "H\n\nB\n\nC",
    }


def _client(post, owner=USER_A.id):
    stores = {"linkedin_posts": [post]}
    patch("src.api.v1.linkedin.BaseRepository", side_effect=lambda n: _FakeRepo(n, stores)).start()
    patch("src.api.v1.linkedin.CampaignService", return_value=_FakeCampaignService(owner)).start()
    return TestClient(app)


def _patch(client, post_id, body):
    return client.patch(f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post_id}", json=body)


def test_owner_edits_draft():
    post = _post()
    res = _patch(
        _client(post), post["id"], {"hook": "New hook", "body": "New body", "cta_text": "CTA"}
    )
    assert res.status_code == 200, res.text
    assert post["hook"] == "New hook"
    assert post["full_content"] == "New hook\n\nNew body\n\nCTA"


def test_foreign_campaign_blocked():
    post = _post()
    res = _patch(_client(post, owner=str(uuid4())), post["id"], {"hook": "x"})
    assert res.status_code == 404
    assert post["hook"] == "H"


@pytest.mark.parametrize("locked", ["published", "publishing", "scheduled"])
def test_locked_statuses_blocked(locked):
    post = _post(status=locked)
    res = _patch(_client(post), post["id"], {"hook": "x"})
    assert res.status_code == 409
    assert post["hook"] == "H"


def test_over_char_limit_rejected():
    post = _post()
    res = _patch(_client(post), post["id"], {"body": "x" * 3001})
    assert res.status_code == 422
    assert post["body"] == "B"
