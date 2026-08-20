"""Contract tests for POST /campaigns/{id}/transition - State Transitions."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from uuid import uuid4

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestTransitionCampaignContract:
    """Contract: Transition endpoint exists and validates input."""

    def test_transition_missing_body_returns_422(self) -> None:
        response = client.post(f"/api/campaigns/{uuid4()}/transition")
        assert response.status_code == 422

    def test_transition_missing_target_state_returns_422(self) -> None:
        response = client.post(
            f"/api/campaigns/{uuid4()}/transition",
            json={},
        )
        assert response.status_code == 422

    def test_transition_invalid_uuid_returns_422(self) -> None:
        response = client.post(
            "/api/campaigns/not-a-uuid/transition",
            json={"target_state": "Ready"},
        )
        assert response.status_code == 422
