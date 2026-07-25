"""Integration tests for API versioning."""

from fastapi.testclient import TestClient

from src.api.api import create_app


class TestAPIVersioning:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_v1_health_endpoint(self) -> None:
        resp = self.client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"]["status"] == "healthy"

    def test_v2_health_endpoint(self) -> None:
        resp = self.client.get("/api/v2/health")
        body = resp.json()

    def test_unversioned_routes_to_latest(self) -> None:
        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"

    def test_unknown_version_returns_404(self) -> None:
        resp = self.client.get("/api/v3/health")
        assert resp.status_code == 404
        body = resp.json()
        assert body["status"] == "error"
