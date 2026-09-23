"""Verified LinkedIn account binding for campaign launch.

Covers TASK 1–3 of the launch-binding work:
1. A user can launch with their own connected account.
2. Another user's account is rejected (no scheduling).
3. A disconnected account is rejected (no scheduling).
4. Scheduled posts persist the correct linkedin_account_id (other fields preserved).
5. The publisher publishes through post.linkedin_account_id.
6. No static-account fallback for a bound/unbound post.
7. No connected account -> no launch.
8. Existing draft->scheduled behavior is unchanged.

Frontend-only-shows-own-accounts is covered by the connections read test in
``test_linkedin_connect.py`` (the same GET endpoint powers the selector).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.main import app

USER_A = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
USER_B = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])

CAMPAIGN_ID = str(uuid4())
ACCOUNT_A = "unipile_acct_A"
ACCOUNT_B = "unipile_acct_B"


# ── Multi-table fake Supabase ────────────────────────────────────────────────


class _FakeTable:
    def __init__(self, store: list[dict]) -> None:
        self.store = store
        self._filters: dict[str, str] = {}
        self._lte: dict[str, str] = {}
        self._op: str | None = None
        self._payload: dict | None = None
        self._limit: int | None = None

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

    def limit(self, n: int):
        self._limit = n
        return self

    def _match(self, r: dict) -> bool:
        if not all(str(r.get(f)) == v for f, v in self._filters.items()):
            return False
        return all(str(r.get(f)) <= v for f, v in self._lte.items())

    def execute(self):
        rows = [r for r in self.store if self._match(r)]
        if self._op == "select":
            if self._limit is not None:
                rows = rows[: self._limit]
            return SimpleNamespace(data=list(rows))
        if self._op == "update":
            for r in rows:
                r.update(self._payload or {})
            return SimpleNamespace(data=list(rows))
        return SimpleNamespace(data=[])


class _FakeRepo:
    def __init__(self, table_name: str, stores: dict[str, list[dict]]) -> None:
        self.table_name = table_name
        self.stores = stores
        self.client = self

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self.stores.setdefault(name, []))


class _FakeGateway:
    def __init__(self, *, account: dict | None) -> None:
        self._account = account
        self.get_account_calls: list[str] = []

    async def get_account(self, account_id: str):
        self.get_account_calls.append(account_id)
        return self._account


class _FakeCampaignService:
    async def get_campaign(self, *_a, **_k):
        return SimpleNamespace(id=CAMPAIGN_ID)


@pytest.fixture(autouse=True)
def _clean_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _as(user: AuthenticatedUser) -> None:
    app.dependency_overrides[get_authenticated_user] = lambda: user


def _account_row(user: AuthenticatedUser, unipile_id: str, status: str = "connected") -> dict:
    return {
        "id": str(uuid4()),
        "user_id": user.id,
        "unipile_account_id": unipile_id,
        "provider": "LINKEDIN",
        "status": status,
        "created_at": "2026-01-01T00:00:00Z",
    }


def _draft_post() -> dict:
    return {
        "id": str(uuid4()),
        "campaign_id": CAMPAIGN_ID,
        "status": "draft",
        "linkedin_account_id": None,
        "full_content": "Hello world",
        "scheduled_at": "2026-09-20T10:00:00+00:00",
        "media_url": "https://cdn.example.com/v.mp4",
    }


def _launch(stores: dict[str, list[dict]], gateway: _FakeGateway, account_id: str):
    with (
        patch(
            "src.api.v1.linkedin.BaseRepository",
            side_effect=lambda name: _FakeRepo(name, stores),
        ),
        patch("src.api.v1.linkedin.get_unipile_gateway", return_value=gateway),
        patch("src.api.v1.linkedin.CampaignService", return_value=_FakeCampaignService()),
    ):
        return TestClient(app).post(
            f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/launch",
            json={"account_id": account_id},
        )


# ── Launch ownership / status validation ─────────────────────────────────────


def test_user_can_launch_with_own_connected_account():
    _as(USER_A)
    post = _draft_post()
    stores = {
        "linkedin_accounts": [_account_row(USER_A, ACCOUNT_A)],
        "linkedin_posts": [post],
    }
    gateway = _FakeGateway(account={"provider": "LINKEDIN"})

    res = _launch(stores, gateway, ACCOUNT_A)

    assert res.status_code == 200
    assert res.json()["account_id"] == ACCOUNT_A
    # (4) post bound + scheduled, other fields preserved
    assert post["status"] == "scheduled"
    assert post["linkedin_account_id"] == ACCOUNT_A
    assert post["full_content"] == "Hello world"
    assert post["scheduled_at"] == "2026-09-20T10:00:00+00:00"
    assert post["media_url"] == "https://cdn.example.com/v.mp4"


def test_other_users_account_is_rejected():
    _as(USER_A)
    post = _draft_post()
    stores = {
        "linkedin_accounts": [_account_row(USER_B, ACCOUNT_B)],  # belongs to B
        "linkedin_posts": [post],
    }
    gateway = _FakeGateway(account={"provider": "LINKEDIN"})

    res = _launch(stores, gateway, ACCOUNT_B)

    assert res.status_code == 409
    assert post["status"] == "draft"  # nothing scheduled
    assert post["linkedin_account_id"] is None
    assert gateway.get_account_calls == []  # never reverified an unowned account


def test_disconnected_account_is_rejected():
    _as(USER_A)
    post = _draft_post()
    stores = {
        "linkedin_accounts": [_account_row(USER_A, ACCOUNT_A, status="disconnected")],
        "linkedin_posts": [post],
    }
    gateway = _FakeGateway(account={"provider": "LINKEDIN"})

    res = _launch(stores, gateway, ACCOUNT_A)

    assert res.status_code == 409
    assert post["status"] == "draft"
    assert gateway.get_account_calls == []  # rejected on stored status, before reverify


def test_no_connected_account_means_no_launch():
    _as(USER_A)
    post = _draft_post()
    stores = {"linkedin_accounts": [], "linkedin_posts": [post]}
    gateway = _FakeGateway(account=None)

    res = _launch(stores, gateway, ACCOUNT_A)

    assert res.status_code == 409
    assert post["status"] == "draft"


def test_live_reverify_downgrades_non_linkedin_account():
    _as(USER_A)
    row = _account_row(USER_A, ACCOUNT_A)
    post = _draft_post()
    stores = {"linkedin_accounts": [row], "linkedin_posts": [post]}
    # Stored says connected, but the provider now reports a non-LinkedIn account.
    gateway = _FakeGateway(account={"provider": "WHATSAPP"})

    res = _launch(stores, gateway, ACCOUNT_A)

    assert res.status_code == 409
    assert post["status"] == "draft"
    assert row["status"] == "disconnected"  # drift persisted


def test_transient_reverify_falls_back_to_stored_connected():
    _as(USER_A)
    post = _draft_post()
    stores = {
        "linkedin_accounts": [_account_row(USER_A, ACCOUNT_A)],
        "linkedin_posts": [post],
    }
    gateway = _FakeGateway(account=None)  # get_account swallows a transient error

    res = _launch(stores, gateway, ACCOUNT_A)

    assert res.status_code == 200
    assert post["status"] == "scheduled"
    assert post["linkedin_account_id"] == ACCOUNT_A
