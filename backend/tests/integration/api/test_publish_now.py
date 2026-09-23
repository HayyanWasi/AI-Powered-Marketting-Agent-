"""Phase D: Safe Publish Now — ownership, brand routing, atomic claim, failure classification.

All external dispatch is a recording in-process mock gateway injected via
dependency/patch. ZERO real Unipile create_post calls, ZERO real LinkedIn posts.

Covered:
- owner publishes a draft (brand account used, not global env)
- foreign user blocked (404)
- no brand account / disconnected account -> 409
- every non-draft status blocked -> 409 (scheduled/publishing/published/failed/needs_review)
- atomic claim: duplicate requests dispatch exactly once; a non-draft claim never dispatches
- confirmed provider rejection (gateway None) -> failed
- ambiguous transport failure (UnipileTransportError) -> needs_review, no retry
- success persists status/unipile_post_id/published_at/linkedin_account_id, other fields intact
- external success + DB finalization failure -> needs_review (never re-dispatched, never draft)
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.gateways.unipile_gateway import UnipileTransportError
from src.main import app

USER_A = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
CAMPAIGN_ID = str(uuid4())
BRAND_ID = str(uuid4())
ACCOUNT_PK = str(uuid4())
BRAND_UNIPILE_ID = "unipile_brand_acct"
GLOBAL_UNIPILE_ID = "unipile_GLOBAL_should_never_be_used"


# ── Multi-table fake Supabase (shared store across both patched BaseRepository) ──


class _FakeTable:
    def __init__(self, store: list[dict], *, raise_on_status: str | None = None) -> None:
        self.store = store
        self._raise_on_status = raise_on_status
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
            payload = self._payload or {}
            # Simulate a DB finalization failure for a specific target status.
            if self._raise_on_status and payload.get("status") == self._raise_on_status:
                raise RuntimeError("Simulated DB write failure")
            for r in rows:
                r.update(payload)
            return SimpleNamespace(data=list(rows))
        return SimpleNamespace(data=[])


class _FakeRepo:
    def __init__(
        self, table_name: str, stores: dict[str, list[dict]], *, raise_on_status=None
    ) -> None:
        self.table_name = table_name
        self.stores = stores
        self._raise_on_status = raise_on_status
        self.client = self

    def table(self, name: str) -> _FakeTable:
        raise_for = self._raise_on_status if name == "linkedin_posts" else None
        return _FakeTable(self.stores.setdefault(name, []), raise_on_status=raise_for)


class _RecordingGateway:
    """Records create_post calls; never touches the network."""

    def __init__(self, *, result="unipile_post_123", raises: Exception | None = None) -> None:
        self._result = result
        self._raises = raises
        self.calls: list[dict] = []

    async def create_post(self, account_id: str, text: str, media_url: str | None = None):
        self.calls.append({"account_id": account_id, "text": text, "media_url": media_url})
        if self._raises is not None:
            raise self._raises
        return self._result


class _FakeCampaignService:
    def __init__(self, *, owner_id: str) -> None:
        self._owner = owner_id

    async def get_campaign(self, campaign_id, user_id, *_a, **_k):
        if str(user_id) != self._owner:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return SimpleNamespace(id=str(campaign_id), company_profile_id=BRAND_ID)


@pytest.fixture(autouse=True)
def _clean():
    app.dependency_overrides.clear()
    # Global env account must never be used by Publish Now; set a sentinel.
    from src.config.settings import settings

    settings.unipile_account_id = GLOBAL_UNIPILE_ID
    yield
    patch.stopall()
    app.dependency_overrides.clear()


def _as(user: AuthenticatedUser) -> None:
    app.dependency_overrides[get_authenticated_user] = lambda: user


def _brand(default_account_pk: str | None = ACCOUNT_PK) -> dict:
    return {"id": BRAND_ID, "user_id": USER_A.id, "default_linkedin_account_id": default_account_pk}


def _account(status: str = "connected") -> dict:
    return {
        "id": ACCOUNT_PK,
        "user_id": USER_A.id,
        "unipile_account_id": BRAND_UNIPILE_ID,
        "provider": "LINKEDIN",
        "status": status,
    }


def _post(status: str = "draft") -> dict:
    return {
        "id": str(uuid4()),
        "campaign_id": CAMPAIGN_ID,
        "status": status,
        "linkedin_account_id": None if status == "draft" else BRAND_UNIPILE_ID,
        "full_content": "Hello LinkedIn world",
        "hook": "Hook",
        "body": "Body",
        "cta_text": "CTA",
        "media_url": None,
        "unipile_post_id": None,
        "published_at": None,
    }


def _stores(post, *, brand=None, account=None) -> dict:
    return {
        "linkedin_posts": [post],
        "company_profiles": [brand if brand is not None else _brand()],
        "linkedin_accounts": [account] if account is not None else [_account()],
    }


def _client(stores, gateway, *, owner=USER_A.id, raise_on_status=None) -> TestClient:
    def _mk(name):
        return _FakeRepo(name, stores, raise_on_status=raise_on_status)

    patch("src.api.v1.autopilot.BaseRepository", side_effect=_mk).start()
    patch("src.api.v1.linkedin.BaseRepository", side_effect=_mk).start()
    patch("src.api.v1.autopilot.get_unipile_gateway", return_value=gateway).start()
    patch(
        "src.api.v1.autopilot.CampaignService", return_value=_FakeCampaignService(owner_id=owner)
    ).start()
    return TestClient(app)


def _publish(client, post_id):
    return client.post(f"/api/v1/autopilot/publish-now/{post_id}")


# ── Success + routing ────────────────────────────────────────────────────────


def test_owner_publishes_draft_with_brand_account():
    _as(USER_A)
    post = _post()
    gw = _RecordingGateway()
    res = _publish(_client(_stores(post), gw), post["id"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    assert body["status"] == "published"
    # Brand account used — NOT the global sentinel.
    assert len(gw.calls) == 1
    assert gw.calls[0]["account_id"] == BRAND_UNIPILE_ID
    assert gw.calls[0]["account_id"] != GLOBAL_UNIPILE_ID
    # Persistence
    assert post["status"] == "published"
    assert post["unipile_post_id"] == "unipile_post_123"
    assert post["published_at"] is not None
    assert post["linkedin_account_id"] == BRAND_UNIPILE_ID
    # Unrelated fields intact
    assert post["hook"] == "Hook" and post["body"] == "Body" and post["cta_text"] == "CTA"


def test_global_settings_account_is_ignored():
    _as(USER_A)
    post = _post()
    gw = _RecordingGateway()
    _publish(_client(_stores(post), gw), post["id"])
    assert all(c["account_id"] != GLOBAL_UNIPILE_ID for c in gw.calls)


# ── Ownership ────────────────────────────────────────────────────────────────


def test_foreign_user_blocked():
    _as(USER_A)
    post = _post()
    gw = _RecordingGateway()
    res = _publish(_client(_stores(post), gw, owner=str(uuid4())), post["id"])
    assert res.status_code == 404
    assert gw.calls == []
    assert post["status"] == "draft"


def test_missing_post_404():
    _as(USER_A)
    post = _post()
    gw = _RecordingGateway()
    res = _publish(_client(_stores(post), gw), str(uuid4()))
    assert res.status_code == 404
    assert gw.calls == []


# ── Account validation ───────────────────────────────────────────────────────


def test_no_brand_account_rejected():
    _as(USER_A)
    post = _post()
    gw = _RecordingGateway()
    res = _publish(_client(_stores(post, brand=_brand(default_account_pk=None)), gw), post["id"])
    assert res.status_code == 409
    assert gw.calls == []
    assert post["status"] == "draft"


def test_disconnected_account_rejected():
    _as(USER_A)
    post = _post()
    gw = _RecordingGateway()
    res = _publish(_client(_stores(post, account=_account(status="disconnected")), gw), post["id"])
    assert res.status_code == 409
    assert gw.calls == []
    assert post["status"] == "draft"


# ── Status guards (draft only) ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad_status", ["scheduled", "publishing", "published", "failed", "needs_review"]
)
def test_non_draft_blocked(bad_status):
    _as(USER_A)
    post = _post(status=bad_status)
    gw = _RecordingGateway()
    res = _publish(_client(_stores(post), gw), post["id"])
    assert res.status_code == 409, f"{bad_status} should be blocked"
    assert gw.calls == []
    assert post["status"] == bad_status  # untouched


# ── Atomic claim / concurrency ───────────────────────────────────────────────


def test_duplicate_requests_dispatch_exactly_once():
    _as(USER_A)
    post = _post()
    gw = _RecordingGateway()
    client = _client(_stores(post), gw)
    first = _publish(client, post["id"])
    second = _publish(client, post["id"])  # post now 'published'
    assert first.status_code == 200
    assert second.status_code == 409
    assert len(gw.calls) == 1  # exactly one external dispatch


def test_claim_guard_blocks_already_claimed_post():
    # The losing racer: a post already in 'publishing' is never dispatched again.
    _as(USER_A)
    post = _post(status="publishing")
    gw = _RecordingGateway()
    res = _publish(_client(_stores(post), gw), post["id"])
    assert res.status_code == 409
    assert gw.calls == []


# ── Failure classification ───────────────────────────────────────────────────


def test_confirmed_provider_rejection_marks_failed():
    _as(USER_A)
    post = _post()
    gw = _RecordingGateway(result=None)  # confirmed non-2xx per gateway contract
    res = _publish(_client(_stores(post), gw), post["id"])
    assert res.status_code == 200  # endpoint returns a result envelope
    body = res.json()
    assert body["success"] is False
    assert body["status"] == "failed"
    assert post["status"] == "failed"
    assert len(gw.calls) == 1


def test_ambiguous_transport_failure_marks_needs_review():
    _as(USER_A)
    post = _post()
    gw = _RecordingGateway(raises=UnipileTransportError("connection reset"))
    res = _publish(_client(_stores(post), gw), post["id"])
    body = res.json()
    assert body["success"] is False
    assert body["status"] == "needs_review"
    assert post["status"] == "needs_review"
    assert len(gw.calls) == 1  # dispatched once, never retried


def test_external_success_but_db_finalization_failure_marks_needs_review():
    _as(USER_A)
    post = _post()
    gw = _RecordingGateway(result="unipile_post_999")
    # Finalization update to 'published' raises; best-effort needs_review must apply.
    res = _publish(_client(_stores(post), gw, raise_on_status="published"), post["id"])
    body = res.json()
    assert body["success"] is False
    assert body["status"] == "needs_review"
    assert post["status"] == "needs_review"
    assert post["unipile_post_id"] == "unipile_post_999"  # id preserved for reconciliation
    assert post["status"] != "draft"  # never reset to draft
    assert len(gw.calls) == 1  # never re-dispatched
