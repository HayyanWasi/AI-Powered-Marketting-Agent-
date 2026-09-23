"""In-app LinkedIn connection (Unipile Hosted Auth) — verified-account foundation.

Covers:
1. Hosted Auth link is generated server-side.
2. Provider is LinkedIn only (never "*").
3. The Unipile API key never reaches the frontend response.
4. The notify callback maps account_id to the correct user.
5. get_account is called to verify real provider state.
6. A non-LinkedIn account is rejected (not persisted).
7. A duplicate callback upserts safely (single row).
8. A user cannot see another user's account; a non-user 'name' is rejected.
9. A user lists only their own connected accounts.
10. Success/failure redirect URLs are wired for the frontend states.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.config.settings import settings
from src.main import app

USER_A = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
USER_B = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])

ACCOUNT_A = "unipile_acct_A"
FAKE_TOKEN = "super-secret-unipile-key-should-never-leak"


# ── Fake Supabase repo (shared in-memory store) ─────────────────────────────


class _FakeTable:
    def __init__(self, store: list[dict]) -> None:
        self.store = store
        self._filters: dict[str, str] = {}
        self._op: str | None = None
        self._payload: dict | None = None
        self._on_conflict: str | None = None

    def select(self, *_a, **_k):
        self._op = "select"
        return self

    def upsert(self, row: dict, on_conflict: str | None = None):
        self._op = "upsert"
        self._payload = row
        self._on_conflict = on_conflict
        return self

    def update(self, payload: dict):
        self._op = "update"
        self._payload = payload
        return self

    def eq(self, field: str, value):
        self._filters[field] = str(value)
        return self

    def order(self, *_a, **_k):
        return self

    def execute(self):
        if self._op == "select":
            rows = [
                r for r in self.store if all(str(r.get(f)) == v for f, v in self._filters.items())
            ]
            return SimpleNamespace(data=list(rows))
        if self._op == "upsert":
            key = self._on_conflict or "id"
            kv = (self._payload or {}).get(key)
            for r in self.store:
                if r.get(key) == kv:
                    r.update(self._payload or {})
                    return SimpleNamespace(data=[r])
            new_row = dict(self._payload or {})
            new_row.setdefault("id", str(uuid4()))
            new_row.setdefault("created_at", "2026-01-01T00:00:00Z")
            self.store.append(new_row)
            return SimpleNamespace(data=[new_row])
        if self._op == "update":
            rows = [
                r for r in self.store if all(str(r.get(f)) == v for f, v in self._filters.items())
            ]
            for r in rows:
                r.update(self._payload or {})
            return SimpleNamespace(data=list(rows))
        return SimpleNamespace(data=[])


class _FakeRepo:
    def __init__(self, table_name: str, store: list[dict]) -> None:
        self.table_name = table_name
        self.store = store
        self.client = self

    def table(self, _name: str) -> _FakeTable:
        return _FakeTable(self.store)


# ── Fake Unipile gateway ────────────────────────────────────────────────────


class _FakeGateway:
    def __init__(self, *, account: dict | None) -> None:
        self.is_configured = True
        self._account = account
        self.link_kwargs: dict | None = None
        self.get_account_calls: list[str] = []

    async def create_hosted_auth_link(self, **kwargs):
        self.link_kwargs = kwargs
        # The real gateway sends the API key only in server-side headers; the
        # returned URL never contains it.
        return "https://account.unipile.com/hosted/abc123"

    async def get_account(self, account_id: str):
        self.get_account_calls.append(account_id)
        return self._account


@pytest.fixture(autouse=True)
def _clean_overrides_and_token(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.setattr(settings, "unipile_token", FAKE_TOKEN, raising=False)
    monkeypatch.setattr(settings, "frontend_base_url", "https://app.example.com", raising=False)
    monkeypatch.setattr(settings, "app_public_base_url", "https://api.example.com", raising=False)
    yield
    app.dependency_overrides.clear()


def _as(user: AuthenticatedUser) -> None:
    app.dependency_overrides[get_authenticated_user] = lambda: user


def _linkedin_account() -> dict:
    return {"id": ACCOUNT_A, "provider": "LINKEDIN", "status": "connected"}


# ── Task 1 / 2 / 3 / 10: hosted auth link ───────────────────────────────────


def test_hosted_auth_link_generated_server_side_linkedin_only_no_key_leak():
    _as(USER_A)
    gateway = _FakeGateway(account=_linkedin_account())
    with patch("src.api.v1.linkedin_connect.get_unipile_gateway", return_value=gateway):
        res = TestClient(app).post("/api/v1/linkedin/connections/link")

    assert res.status_code == 200
    body = res.json()
    # (1) link generated server-side, returned to frontend
    assert body["url"].startswith("https://account.unipile.com/")
    # (2) provider LinkedIn only, never "*"
    assert gateway.link_kwargs["providers"] == ["LINKEDIN"]
    assert gateway.link_kwargs["name"] == USER_A.id  # tied to the authed user
    # (10) success/failure redirect states wired for the frontend
    assert "linkedin=connected" in gateway.link_kwargs["success_redirect_url"]
    assert "linkedin=failed" in gateway.link_kwargs["failure_redirect_url"]
    assert gateway.link_kwargs["notify_url"].endswith("/api/v1/linkedin/connections/notify")
    # (3) API key never reaches the frontend
    assert FAKE_TOKEN not in res.text
    assert set(body.keys()) == {"url"}


def test_hosted_auth_link_requires_configured_unipile():
    _as(USER_A)
    gateway = _FakeGateway(account=None)
    gateway.is_configured = False
    with patch("src.api.v1.linkedin_connect.get_unipile_gateway", return_value=gateway):
        res = TestClient(app).post("/api/v1/linkedin/connections/link")
    assert res.status_code == 503


# ── Task 2 (callback) / 4 / 5: notify persistence + verification ─────────────


def test_notify_maps_account_to_correct_user_after_verification():
    store: list[dict] = []
    gateway = _FakeGateway(account=_linkedin_account())
    with (
        patch(
            "src.api.v1.linkedin_connect.BaseRepository",
            side_effect=lambda name: _FakeRepo(name, store),
        ),
        patch("src.api.v1.linkedin_connect.get_unipile_gateway", return_value=gateway),
    ):
        res = TestClient(app).post(
            "/api/v1/linkedin/connections/notify",
            json={"status": "CREATION_SUCCESS", "account_id": ACCOUNT_A, "name": USER_A.id},
        )

    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    # (5) real provider state verified
    assert gateway.get_account_calls == [ACCOUNT_A]
    # (4) mapping persisted to the correct user
    assert len(store) == 1
    assert store[0]["user_id"] == USER_A.id
    assert store[0]["unipile_account_id"] == ACCOUNT_A
    assert store[0]["provider"] == "LINKEDIN"
    assert store[0]["status"] == "connected"


# ── Task 2: rejection paths ─────────────────────────────────────────────────


def test_non_linkedin_account_is_rejected_and_not_persisted():
    store: list[dict] = []
    gateway = _FakeGateway(account={"id": ACCOUNT_A, "provider": "WHATSAPP"})
    with (
        patch(
            "src.api.v1.linkedin_connect.BaseRepository",
            side_effect=lambda name: _FakeRepo(name, store),
        ),
        patch("src.api.v1.linkedin_connect.get_unipile_gateway", return_value=gateway),
    ):
        res = TestClient(app).post(
            "/api/v1/linkedin/connections/notify",
            json={"status": "CREATION_SUCCESS", "account_id": ACCOUNT_A, "name": USER_A.id},
        )

    assert res.json()["status"] == "rejected"
    assert store == []


def test_notify_rejects_non_user_name():
    store: list[dict] = []
    gateway = _FakeGateway(account=_linkedin_account())
    with (
        patch(
            "src.api.v1.linkedin_connect.BaseRepository",
            side_effect=lambda name: _FakeRepo(name, store),
        ),
        patch("src.api.v1.linkedin_connect.get_unipile_gateway", return_value=gateway),
    ):
        res = TestClient(app).post(
            "/api/v1/linkedin/connections/notify",
            json={"status": "CREATION_SUCCESS", "account_id": ACCOUNT_A, "name": "not-a-uuid"},
        )

    assert res.json()["status"] == "rejected"
    assert store == []
    assert gateway.get_account_calls == []  # never verified an unowned name


def test_notify_ignores_unsuccessful_status():
    store: list[dict] = []
    gateway = _FakeGateway(account=_linkedin_account())
    with (
        patch(
            "src.api.v1.linkedin_connect.BaseRepository",
            side_effect=lambda name: _FakeRepo(name, store),
        ),
        patch("src.api.v1.linkedin_connect.get_unipile_gateway", return_value=gateway),
    ):
        res = TestClient(app).post(
            "/api/v1/linkedin/connections/notify",
            json={"status": "CREATION_FAILED", "account_id": ACCOUNT_A, "name": USER_A.id},
        )

    assert res.json()["status"] == "ignored"
    assert store == []


# ── Task 2: idempotency ──────────────────────────────────────────────────────


def test_duplicate_callback_upserts_safely():
    store: list[dict] = []
    gateway = _FakeGateway(account=_linkedin_account())
    with (
        patch(
            "src.api.v1.linkedin_connect.BaseRepository",
            side_effect=lambda name: _FakeRepo(name, store),
        ),
        patch("src.api.v1.linkedin_connect.get_unipile_gateway", return_value=gateway),
    ):
        client = TestClient(app)
        payload = {"status": "CREATION_SUCCESS", "account_id": ACCOUNT_A, "name": USER_A.id}
        client.post("/api/v1/linkedin/connections/notify", json=payload)
        client.post("/api/v1/linkedin/connections/notify", json=payload)  # duplicate
        # reconnect status for the same account should also not duplicate
        client.post(
            "/api/v1/linkedin/connections/notify",
            json={"status": "RECONNECTED", "account_id": ACCOUNT_A, "name": USER_A.id},
        )

    assert len(store) == 1


# ── Task 4: ownership on read ────────────────────────────────────────────────


def test_user_lists_only_their_own_accounts():
    store: list[dict] = [
        {
            "id": str(uuid4()),
            "user_id": USER_A.id,
            "unipile_account_id": ACCOUNT_A,
            "provider": "LINKEDIN",
            "status": "connected",
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]

    # USER_A sees their account.
    _as(USER_A)
    with patch(
        "src.api.v1.linkedin_connect.BaseRepository",
        side_effect=lambda name: _FakeRepo(name, store),
    ):
        res_a = TestClient(app).get("/api/v1/linkedin/connections")
    assert res_a.status_code == 200
    rows_a = res_a.json()
    assert len(rows_a) == 1
    assert rows_a[0]["unipile_account_id"] == ACCOUNT_A

    # USER_B must never see USER_A's account.
    _as(USER_B)
    with patch(
        "src.api.v1.linkedin_connect.BaseRepository",
        side_effect=lambda name: _FakeRepo(name, store),
    ):
        res_b = TestClient(app).get("/api/v1/linkedin/connections")
    assert res_b.status_code == 200
    assert res_b.json() == []


def test_list_verify_refreshes_live_status():
    store: list[dict] = [
        {
            "id": str(uuid4()),
            "user_id": USER_A.id,
            "unipile_account_id": ACCOUNT_A,
            "provider": "LINKEDIN",
            "status": "connected",
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]
    _as(USER_A)
    gateway = _FakeGateway(account=None)  # provider now reports gone
    with (
        patch(
            "src.api.v1.linkedin_connect.BaseRepository",
            side_effect=lambda name: _FakeRepo(name, store),
        ),
        patch("src.api.v1.linkedin_connect.get_unipile_gateway", return_value=gateway),
    ):
        res = TestClient(app).get("/api/v1/linkedin/connections?verify=true")

    assert res.status_code == 200
    assert res.json()[0]["status"] == "disconnected"
    assert store[0]["status"] == "disconnected"  # persisted
