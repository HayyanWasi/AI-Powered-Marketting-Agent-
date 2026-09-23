"""Phase C: per-post schedule / reschedule / cancel contract.

Covers the safe scheduling flow without ever publishing or contacting LinkedIn:
- schedule a draft using the brand's default account (account derived, not client-supplied)
- brand has no default account / disconnected account -> 409
- non-draft post -> 409
- past / naive datetime -> 422
- content over the LinkedIn limit -> 409/422
- reschedule a scheduled post (account + content preserved)
- reschedule/cancel LOSE the race to a worker claim ('publishing') -> 409
- cancel returns the post to draft and clears scheduled_at + account binding
- cross-user campaign is rejected before any mutation
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
BRAND_ID = str(uuid4())
ACCOUNT_PK = str(uuid4())
UNIPILE_ID = "unipile_acct_A"

FUTURE = (datetime.now(UTC) + timedelta(days=2)).isoformat()
PAST = (datetime.now(UTC) - timedelta(days=1)).isoformat()
NAIVE = (datetime.now() + timedelta(days=2)).replace(tzinfo=None).isoformat()


# ── Multi-table fake Supabase ────────────────────────────────────────────────


class _FakeTable:
    def __init__(self, store: list[dict]) -> None:
        self.store = store
        self._filters: dict[str, str] = {}
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

    def order(self, *_a, **_k):
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def _match(self, r: dict) -> bool:
        return all(str(r.get(f)) == v for f, v in self._filters.items())

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


class _FakeCampaignService:
    def __init__(self, *, owner_id: str, company_profile_id: str | None) -> None:
        self._owner = owner_id
        self._cpid = company_profile_id

    async def get_campaign(self, campaign_id, user_id, *_a, **_k):
        if str(user_id) != self._owner:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return SimpleNamespace(id=str(campaign_id), company_profile_id=self._cpid)


@pytest.fixture(autouse=True)
def _clean_overrides():
    app.dependency_overrides.clear()
    yield
    patch.stopall()  # stop any _client() patches even if a test asserted early
    app.dependency_overrides.clear()


def _as(user: AuthenticatedUser) -> None:
    app.dependency_overrides[get_authenticated_user] = lambda: user


def _brand(default_account_pk: str | None = ACCOUNT_PK) -> dict:
    return {"id": BRAND_ID, "user_id": USER_A.id, "default_linkedin_account_id": default_account_pk}


def _account(status: str = "connected") -> dict:
    return {
        "id": ACCOUNT_PK,
        "user_id": USER_A.id,
        "unipile_account_id": UNIPILE_ID,
        "provider": "LINKEDIN",
        "status": status,
    }


def _post(status: str = "draft", full_content: str = "Hello world") -> dict:
    return {
        "id": str(uuid4()),
        "campaign_id": CAMPAIGN_ID,
        "status": status,
        "linkedin_account_id": None if status == "draft" else UNIPILE_ID,
        "full_content": full_content,
        "scheduled_at": None if status == "draft" else "2026-09-20T10:00:00+00:00",
        "media_url": "https://cdn.example.com/v.mp4",
        "hook": "Hook",
    }


def _client(stores: dict, *, owner=USER_A.id, cpid=BRAND_ID) -> TestClient:
    svc = _FakeCampaignService(owner_id=owner, company_profile_id=cpid)
    patches = [
        patch("src.api.v1.linkedin.BaseRepository", side_effect=lambda name: _FakeRepo(name, stores)),
        patch("src.api.v1.linkedin.CampaignService", return_value=svc),
    ]
    for p in patches:
        p.start()
    return TestClient(app)


def _stores(post: dict, *, brand: dict | None = None, account: dict | None = None) -> dict:
    return {
        "linkedin_posts": [post],
        "company_profiles": [brand if brand is not None else _brand()],
        "linkedin_accounts": [account] if account is not None else [_account()],
    }


# ── Schedule ─────────────────────────────────────────────────────────────────


def test_schedule_draft_binds_brand_account():
    _as(USER_A)
    post = _post()
    stores = _stores(post)
    client = _client(stores)
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/schedule",
        json={"scheduled_at": FUTURE, "timezone": "America/New_York"},
    )
    patch.stopall()
    assert res.status_code == 200, res.text
    assert post["status"] == "scheduled"
    assert post["linkedin_account_id"] == UNIPILE_ID  # derived from brand, not client
    assert post["timezone"] == "America/New_York"
    assert post["scheduled_at"].startswith(FUTURE[:10])


def test_schedule_without_brand_account_rejected():
    _as(USER_A)
    post = _post()
    stores = _stores(post, brand=_brand(default_account_pk=None))
    client = _client(stores)
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/schedule",
        json={"scheduled_at": FUTURE, "timezone": "UTC"},
    )
    patch.stopall()
    assert res.status_code == 409
    assert post["status"] == "draft"


def test_schedule_with_disconnected_account_rejected():
    _as(USER_A)
    post = _post()
    stores = _stores(post, account=_account(status="disconnected"))
    client = _client(stores)
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/schedule",
        json={"scheduled_at": FUTURE, "timezone": "UTC"},
    )
    patch.stopall()
    assert res.status_code == 409
    assert post["status"] == "draft"


def test_schedule_past_datetime_rejected():
    _as(USER_A)
    post = _post()
    client = _client(_stores(post))
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/schedule",
        json={"scheduled_at": PAST, "timezone": "UTC"},
    )
    patch.stopall()
    assert res.status_code == 422
    assert post["status"] == "draft"


def test_schedule_naive_datetime_rejected():
    _as(USER_A)
    post = _post()
    client = _client(_stores(post))
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/schedule",
        json={"scheduled_at": NAIVE, "timezone": "UTC"},
    )
    patch.stopall()
    assert res.status_code == 422
    assert post["status"] == "draft"


def test_schedule_non_draft_rejected():
    _as(USER_A)
    post = _post(status="published")
    client = _client(_stores(post))
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/schedule",
        json={"scheduled_at": FUTURE, "timezone": "UTC"},
    )
    patch.stopall()
    assert res.status_code == 409
    assert post["status"] == "published"


def test_schedule_over_limit_rejected():
    _as(USER_A)
    post = _post(full_content="x" * 3001)
    client = _client(_stores(post))
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/schedule",
        json={"scheduled_at": FUTURE, "timezone": "UTC"},
    )
    patch.stopall()
    assert res.status_code == 422
    assert post["status"] == "draft"


def test_schedule_foreign_campaign_rejected():
    _as(USER_A)
    post = _post()
    client = _client(_stores(post), owner=str(uuid4()))  # campaign owned by someone else
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/schedule",
        json={"scheduled_at": FUTURE, "timezone": "UTC"},
    )
    patch.stopall()
    assert res.status_code == 404
    assert post["status"] == "draft"


def test_schedule_requires_auth():
    # No auth override installed -> dependency rejects.
    post = _post()
    client = _client(_stores(post))
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/schedule",
        json={"scheduled_at": FUTURE, "timezone": "UTC"},
    )
    patch.stopall()
    assert res.status_code in (401, 403)


# ── Reschedule ───────────────────────────────────────────────────────────────


def test_reschedule_scheduled_post_preserves_binding():
    _as(USER_A)
    post = _post(status="scheduled")
    original_content = post["full_content"]
    client = _client(_stores(post))
    new_time = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/reschedule",
        json={"scheduled_at": new_time, "timezone": "Europe/London"},
    )
    patch.stopall()
    assert res.status_code == 200, res.text
    assert post["status"] == "scheduled"
    assert post["linkedin_account_id"] == UNIPILE_ID  # preserved
    assert post["full_content"] == original_content  # preserved
    assert post["timezone"] == "Europe/London"


def test_reschedule_loses_race_to_publishing():
    _as(USER_A)
    post = _post(status="publishing")  # worker already claimed it
    client = _client(_stores(post))
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/reschedule",
        json={"scheduled_at": FUTURE, "timezone": "UTC"},
    )
    patch.stopall()
    assert res.status_code == 409
    assert post["status"] == "publishing"  # untouched


# ── Cancel ───────────────────────────────────────────────────────────────────


def test_cancel_scheduled_returns_to_draft():
    _as(USER_A)
    post = _post(status="scheduled")
    client = _client(_stores(post))
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/cancel-schedule",
    )
    patch.stopall()
    assert res.status_code == 200, res.text
    assert post["status"] == "draft"
    assert post["scheduled_at"] is None
    assert post["linkedin_account_id"] is None
    assert post["full_content"] == "Hello world"  # content preserved


def test_cancel_loses_race_to_publishing():
    _as(USER_A)
    post = _post(status="publishing")
    client = _client(_stores(post))
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/cancel-schedule",
    )
    patch.stopall()
    assert res.status_code == 409
    assert post["status"] == "publishing"


def test_cancel_published_rejected():
    _as(USER_A)
    post = _post(status="published")
    client = _client(_stores(post))
    res = client.post(
        f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/posts/{post['id']}/cancel-schedule",
    )
    patch.stopall()
    assert res.status_code == 409
    assert post["status"] == "published"
