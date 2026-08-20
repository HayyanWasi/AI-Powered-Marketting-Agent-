"""Integration tests for API authentication."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_authenticated_user
from src.api.response import success_response


class TestAuthentication:
    def setup_method(self) -> None:
        self.app = FastAPI()

        @self.app.get("/api/v1/protected")
        async def protected_route(user=Depends(get_authenticated_user)):
            return success_response(data={"user_id": user.id})

        self.client = TestClient(self.app)

    def test_protected_endpoint_with_auth(self) -> None:
        resp = self.client.get("/api/v1/protected")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "user_id" in body["data"]
