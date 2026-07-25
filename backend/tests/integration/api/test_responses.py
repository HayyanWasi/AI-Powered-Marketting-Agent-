"""Integration tests for standardized response envelopes."""

from fastapi.testclient import TestClient

from src.api.api import create_app


class TestStandardizedResponses:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_success_response_envelope_fields(self) -> None:
        resp = self.client.get("/api/v1/health")
        body = resp.json()
        assert "status" in body
        assert "data" in body
        assert "message" in body
        assert "timestamp" in body
        assert body["status"] == "success"

    def test_404_response_envelope(self) -> None:
        resp = self.client.get("/api/v1/nonexistent")
        body = resp.json()
        assert body["status"] == "error"
        assert "error" in body
        assert "message" in body
        assert "timestamp" in body

    def test_response_has_iso_timestamp(self) -> None:
        resp = self.client.get("/api/v1/health")
        body = resp.json()
        ts = body["timestamp"]
        assert ts.endswith("Z") or "+" in ts
