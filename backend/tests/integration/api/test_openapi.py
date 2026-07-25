"""Integration tests for OpenAPI documentation generation."""

from fastapi.testclient import TestClient

from src.api.api import create_app


class TestOpenAPIDocumentation:
    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_swagger_ui_endpoint(self) -> None:
        resp = self.client.get("/docs")
        assert resp.status_code == 200
        assert "swagger" in resp.text.lower()

    def test_redoc_endpoint(self) -> None:
        resp = self.client.get("/redoc")
        assert resp.status_code == 200

    def test_openapi_json_endpoint(self) -> None:
        resp = self.client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "AI Marketing Agent API"
        assert "paths" in schema
        assert len(schema["paths"]) > 0

    def test_endpoints_grouped_by_tag(self) -> None:
        resp = self.client.get("/openapi.json")
        schema = resp.json()
        paths = schema["paths"]
        health_paths = [p for p in paths if "health" in p]
        assert len(health_paths) > 0
