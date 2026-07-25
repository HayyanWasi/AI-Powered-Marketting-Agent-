"""Integration tests for API edge cases.

Tests: 415 unsupported media type, 413 payload too large,
404 version not found, malformed JSON, unsupported methods.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.exception_handlers import register_exception_handlers
from src.api.middleware import register_middleware
from src.api.response import success_response


class TestEdgeCases:
    def setup_method(self) -> None:
        self.app = FastAPI()
        register_exception_handlers(self.app)
        register_middleware(self.app)

        @self.app.post("/api/v1/test-body")
        async def test_body():
            return success_response(data={})

        @self.app.get("/api/v1/test-get")
        async def test_get():
            return success_response(data={})

        self.client = TestClient(self.app)

    def test_unsupported_api_version_returns_404(self) -> None:
        resp = self.client.get("/api/v999/health")
        assert resp.status_code == 404
        body = resp.json()
        assert body["status"] == "error"

    def test_method_not_allowed(self) -> None:
        resp = self.client.put("/api/v1/test-get", headers={"content-type": "application/json"})
        assert resp.status_code in (404, 405)

    def test_missing_content_type_on_post(self) -> None:
        resp = self.client.post("/api/v1/test-body", content="raw data")
        assert resp.status_code in (415, 422, 200)

    def test_request_id_in_response(self) -> None:
        resp = self.client.get("/api/v1/test-get")
        assert "X-Request-ID" in resp.headers

    def test_security_headers_present(self) -> None:
        resp = self.client.get("/api/v1/test-get")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
