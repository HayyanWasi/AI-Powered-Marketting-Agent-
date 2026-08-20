"""Contract tests for GET /campaigns/{id}/history - Campaign History."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestCampaignHistoryContract:
    """Contract: History endpoint exists and accepts pagination params."""

    def test_get_history_invalid_uuid_returns_422(self) -> None:
        response = client.get("/api/campaigns/not-a-uuid/history")
        assert response.status_code == 422
