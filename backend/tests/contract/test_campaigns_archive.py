"""Contract tests for POST /campaigns/{id}/archive and restore."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


class TestArchiveRestoreContract:
    """Contract: Archive and restore endpoints exist and validate input."""

    def test_archive_invalid_uuid_returns_422(self) -> None:
        response = client.post("/campaigns/not-a-uuid/archive")
        assert response.status_code == 422

    def test_restore_invalid_uuid_returns_422(self) -> None:
        response = client.post("/campaigns/not-a-uuid/restore")
        assert response.status_code == 422
