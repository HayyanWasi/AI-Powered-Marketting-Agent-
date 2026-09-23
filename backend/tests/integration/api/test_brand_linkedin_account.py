"""Phase C: Brand <-> default LinkedIn account binding.

The endpoint (``PUT /company/{id}/linkedin-account``) enforces ownership on BOTH
sides: the brand must belong to the caller and the LinkedIn account must be a
connected row the caller owns. Foreign/unknown/disconnected accounts are
rejected and nothing changes. ``account_id: null`` clears the binding.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import src.api.v1.company as company_api
from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.main import app

USER_A = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
BRAND_ID = str(uuid4())
ACCOUNT_PK = str(uuid4())


class _FakeTable:
    def __init__(self, store: list[dict]) -> None:
        self.store = store
        self._filters: dict[str, str] = {}
        self._limit: int | None = None

    def select(self, *_a, **_k):
        return self

    def eq(self, f, v):
        self._filters[f] = str(v)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        rows = [r for r in self.store if all(str(r.get(f)) == v for f, v in self._filters.items())]
        if self._limit is not None:
            rows = rows[: self._limit]
        return SimpleNamespace(data=list(rows))


class _FakeRepo:
    def __init__(self, name, stores):
        self.table_name = name
        self.stores = stores
        self.client = self

    def table(self, name):
        return _FakeTable(self.stores.setdefault(name, []))


class _FakeGetService:
    def __init__(self, owned: bool):
        self._owned = owned

    def execute(self, profile_id):
        if not self._owned:
            raise ValueError("Company profile not found")
        return {"id": profile_id, "company_name": "Acme"}


class _FakeUpdateService:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def execute(self, profile_id, data):
        self.calls.append((profile_id, data))
        return SimpleNamespace(
            id=profile_id,
            company_name="Acme",
            brand_guidelines="{}",
            brand_tone=None,
            reference_image_urls=[],
            default_linkedin_account_id=data.get("default_linkedin_account_id"),
            created_at="t",
            updated_at="t",
        )


@pytest.fixture(autouse=True)
def _clean():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_authenticated_user] = lambda: USER_A
    yield
    patch.stopall()
    app.dependency_overrides.clear()


def _account(status="connected", user_id=USER_A.id):
    return {"id": ACCOUNT_PK, "user_id": user_id, "unipile_account_id": "u_a", "status": status}


def _run(body: dict, *, owned=True, accounts=None):
    update = _FakeUpdateService()
    app.dependency_overrides[company_api._get_get_service] = lambda: _FakeGetService(owned)
    app.dependency_overrides[company_api._get_update_service] = lambda: update
    stores = {"linkedin_accounts": accounts if accounts is not None else [_account()]}
    patch.object(company_api, "BaseRepository", side_effect=lambda name: _FakeRepo(name, stores)).start()
    res = TestClient(app).put(f"/api/v1/company/{BRAND_ID}/linkedin-account", json=body)
    return res, update


def test_owner_assigns_owned_connected_account():
    res, update = _run({"account_id": ACCOUNT_PK})
    assert res.status_code == 200, res.text
    assert res.json()["default_linkedin_account_id"] == ACCOUNT_PK
    assert update.calls == [(BRAND_ID, {"default_linkedin_account_id": ACCOUNT_PK})]


def test_owner_clears_account():
    res, update = _run({"account_id": None})
    assert res.status_code == 200
    assert res.json()["default_linkedin_account_id"] is None
    assert update.calls == [(BRAND_ID, {"default_linkedin_account_id": None})]


def test_foreign_brand_blocked():
    res, update = _run({"account_id": ACCOUNT_PK}, owned=False)
    assert res.status_code == 404
    assert update.calls == []  # never persisted


def test_foreign_account_blocked():
    res, update = _run(
        {"account_id": ACCOUNT_PK}, accounts=[_account(user_id=str(uuid4()))]
    )
    assert res.status_code == 404
    assert update.calls == []


def test_nonexistent_account_blocked():
    res, update = _run({"account_id": ACCOUNT_PK}, accounts=[])
    assert res.status_code == 404
    assert update.calls == []


def test_disconnected_account_blocked():
    res, update = _run({"account_id": ACCOUNT_PK}, accounts=[_account(status="disconnected")])
    assert res.status_code == 409
    assert update.calls == []
