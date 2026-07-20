"""Contract tests for POST /campaigns - Create Campaign."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


class TestCreateCampaignContract:
    """Contract: POST /campaigns endpoint exists and validates input."""

    def test_create_campaign_missing_body_returns_422(self) -> None:
        response = client.post("/campaigns")
        assert response.status_code == 422

    def test_create_campaign_missing_name_returns_422(self) -> None:
        response = client.post(
            "/campaigns",
            json={"goals": {}, "platforms": []},
        )
        assert response.status_code == 422

    def test_create_campaign_empty_body_returns_422(self) -> None:
        response = client.post("/campaigns", json={})
        assert response.status_code == 422
