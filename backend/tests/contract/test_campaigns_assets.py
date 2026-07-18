"""Contract tests for POST/GET /campaigns/{id}/assets - Campaign Assets."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


class TestCampaignAssetsContract:
    """Contract: Asset endpoints exist and validate input."""

    def test_create_asset_missing_body_returns_422(self) -> None:
        from uuid import uuid4

        response = client.post(f"/campaigns/{uuid4()}/assets")
        assert response.status_code == 422

    def test_create_asset_invalid_uuid_returns_422(self) -> None:
        response = client.post(
            "/campaigns/not-a-uuid/assets",
            json={"asset_type": "copy", "content": {}, "source": "ai"},
        )
        assert response.status_code == 422

    def test_list_assets_invalid_uuid_returns_422(self) -> None:
        response = client.get("/campaigns/not-a-uuid/assets")
        assert response.status_code == 422
