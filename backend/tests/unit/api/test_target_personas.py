"""Dedicated unit tests for Target Persona API, legacy account_id exclusion, brand isolation, and security refinement."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.main import app
from tests.unit.api.test_engagement_safety import MockSupabaseClient


@pytest.fixture
def test_setup():
    user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    other_user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    brand_1_id = str(uuid4())
    brand_2_id = str(uuid4())
    other_brand_id = str(uuid4())
    persona_1_id = str(uuid4())
    other_persona_id = str(uuid4())

    stores = {
        "company_profiles": [
            {"id": brand_1_id, "user_id": user.id, "name": "Brand 1"},
            {"id": brand_2_id, "user_id": user.id, "name": "Brand 2"},
            {"id": other_brand_id, "user_id": other_user.id, "name": "Other Brand"},
        ],
        "linkedin_target_personas": [
            {
                "id": persona_1_id,
                "user_id": user.id,
                "company_profile_id": brand_1_id,
                "label": "AI Founders",
                "search_keywords": "AI founder CEO",
                "max_profiles": 100,
                "is_active": True,
                "created_at": datetime.now(UTC).isoformat(),
            },
            {
                "id": other_persona_id,
                "user_id": other_user.id,
                "company_profile_id": other_brand_id,
                "label": "Other Persona",
                "search_keywords": "CTO",
                "max_profiles": 50,
                "is_active": True,
                "created_at": datetime.now(UTC).isoformat(),
            },
        ],
    }
    mock_client = MockSupabaseClient(stores)
    return {
        "user": user,
        "other_user": other_user,
        "brand_1_id": brand_1_id,
        "brand_2_id": brand_2_id,
        "other_brand_id": other_brand_id,
        "persona_1_id": persona_1_id,
        "other_persona_id": other_persona_id,
        "stores": stores,
        "mock_client": mock_client,
    }


def test_create_persona_canonical_payload_no_account_id(test_setup):
    user = test_setup["user"]
    brand_1_id = test_setup["brand_1_id"]
    mock_client = test_setup["mock_client"]

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        patch("src.gateways.unipile_gateway.get_unipile_gateway") as mock_gw,
        TestClient(app) as client,
    ):
        resp = client.post(
            "/api/v1/autopilot/personas",
            json={
                "company_profile_id": brand_1_id,
                "label": "SaaS Leaders",
                "search_keywords": "saas founder b2b",
                "max_profiles": 120,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["success"] is True
        persona = data["persona"]
        assert persona["label"] == "SaaS Leaders"
        assert persona["company_profile_id"] == brand_1_id
        assert persona["user_id"] == user.id
        assert "account_id" not in persona

        # Inspect the raw stored records in mock DB
        all_personas = test_setup["stores"]["linkedin_target_personas"]
        created = [p for p in all_personas if p["label"] == "SaaS Leaders"][0]
        assert "account_id" not in created
        assert created["company_profile_id"] == brand_1_id
        assert created["user_id"] == user.id

        # Zero external actions
        mock_gw.assert_not_called()
    app.dependency_overrides.clear()


def test_update_persona_missing_query_param_422(test_setup):
    user = test_setup["user"]
    persona_1_id = test_setup["persona_1_id"]
    mock_client = test_setup["mock_client"]

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        resp = client.put(
            f"/api/v1/autopilot/personas/{persona_1_id}",
            json={"label": "New Label"},
        )
        assert resp.status_code == 422
    app.dependency_overrides.clear()


def test_update_persona_not_found_404(test_setup):
    user = test_setup["user"]
    brand_1_id = test_setup["brand_1_id"]
    mock_client = test_setup["mock_client"]
    non_existent_id = str(uuid4())

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        resp = client.put(
            f"/api/v1/autopilot/personas/{non_existent_id}?company_profile_id={brand_1_id}",
            json={"label": "New Label"},
        )
        assert resp.status_code == 404
        assert "Persona not found" in resp.text
    app.dependency_overrides.clear()


def test_update_persona_belonging_to_another_user_returns_404(test_setup):
    user = test_setup["user"]
    brand_1_id = test_setup["brand_1_id"]
    other_persona_id = test_setup["other_persona_id"]
    mock_client = test_setup["mock_client"]

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        resp = client.put(
            f"/api/v1/autopilot/personas/{other_persona_id}?company_profile_id={brand_1_id}",
            json={"label": "Hacked Label"},
        )
        # Security refinement: return 404 to avoid exposing existence of another user's persona
        assert resp.status_code == 404
        assert "Persona not found" in resp.text
    app.dependency_overrides.clear()


def test_update_persona_different_brand_same_user_returns_403(test_setup):
    user = test_setup["user"]
    brand_2_id = test_setup["brand_2_id"]
    persona_1_id = test_setup["persona_1_id"]
    mock_client = test_setup["mock_client"]

    # persona_1 belongs to brand_1. User tries to update it under brand_2 context.
    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        resp = client.put(
            f"/api/v1/autopilot/personas/{persona_1_id}?company_profile_id={brand_2_id}",
            json={"label": "Cross-brand update"},
        )
        assert resp.status_code == 403
        assert "Persona does not belong to the specified brand profile" in resp.text
    app.dependency_overrides.clear()


def test_update_persona_same_brand_succeeds(test_setup):
    user = test_setup["user"]
    brand_1_id = test_setup["brand_1_id"]
    persona_1_id = test_setup["persona_1_id"]
    mock_client = test_setup["mock_client"]

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        resp = client.put(
            f"/api/v1/autopilot/personas/{persona_1_id}?company_profile_id={brand_1_id}",
            json={"label": "Updated AI Founders", "max_profiles": 200},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["persona"]["label"] == "Updated AI Founders"
        assert data["persona"]["max_profiles"] == 200
    app.dependency_overrides.clear()


def test_delete_persona_missing_query_param_422(test_setup):
    user = test_setup["user"]
    persona_1_id = test_setup["persona_1_id"]
    mock_client = test_setup["mock_client"]

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        resp = client.delete(f"/api/v1/autopilot/personas/{persona_1_id}")
        assert resp.status_code == 422
    app.dependency_overrides.clear()


def test_delete_persona_not_found_404(test_setup):
    user = test_setup["user"]
    brand_1_id = test_setup["brand_1_id"]
    mock_client = test_setup["mock_client"]
    non_existent_id = str(uuid4())

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        resp = client.delete(
            f"/api/v1/autopilot/personas/{non_existent_id}?company_profile_id={brand_1_id}"
        )
        assert resp.status_code == 404
        assert "Persona not found" in resp.text
    app.dependency_overrides.clear()


def test_delete_persona_belonging_to_another_user_returns_404(test_setup):
    user = test_setup["user"]
    brand_1_id = test_setup["brand_1_id"]
    other_persona_id = test_setup["other_persona_id"]
    mock_client = test_setup["mock_client"]

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        resp = client.delete(
            f"/api/v1/autopilot/personas/{other_persona_id}?company_profile_id={brand_1_id}"
        )
        # Security refinement: return 404 to avoid exposing existence of another user's persona
        assert resp.status_code == 404
        assert "Persona not found" in resp.text
    app.dependency_overrides.clear()


def test_delete_persona_different_brand_same_user_returns_403(test_setup):
    user = test_setup["user"]
    brand_2_id = test_setup["brand_2_id"]
    persona_1_id = test_setup["persona_1_id"]
    mock_client = test_setup["mock_client"]

    # persona_1 belongs to brand_1. User tries to delete it under brand_2 context.
    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        resp = client.delete(
            f"/api/v1/autopilot/personas/{persona_1_id}?company_profile_id={brand_2_id}"
        )
        assert resp.status_code == 403
        assert "Persona does not belong to the specified brand profile" in resp.text
    app.dependency_overrides.clear()


def test_delete_persona_same_brand_succeeds(test_setup):
    user = test_setup["user"]
    brand_1_id = test_setup["brand_1_id"]
    persona_1_id = test_setup["persona_1_id"]
    mock_client = test_setup["mock_client"]

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        resp = client.delete(
            f"/api/v1/autopilot/personas/{persona_1_id}?company_profile_id={brand_1_id}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["id"] == persona_1_id

        # Check it is removed from mock store
        remaining = [
            p for p in test_setup["stores"]["linkedin_target_personas"] if p["id"] == persona_1_id
        ]
        assert len(remaining) == 0
    app.dependency_overrides.clear()
