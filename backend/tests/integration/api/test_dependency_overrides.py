"""Integration tests for FastAPI dependency override support."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.api.response import success_response


async def mock_authenticated_user() -> AuthenticatedUser:
    return AuthenticatedUser(id="test-mock-user", roles=["tester"], permissions=["test"])


class TestDependencyOverrides:
    def setup_method(self) -> None:
        self.app = FastAPI()

        @self.app.get("/api/v1/test-dep")
        async def test_dep(user: AuthenticatedUser = Depends(get_authenticated_user)):
            return success_response(data={"user_id": user.id, "roles": user.roles})

        self.client = TestClient(self.app)

    def test_dependency_override(self) -> None:
        self.app.dependency_overrides[get_authenticated_user] = mock_authenticated_user
        resp = self.client.get("/api/v1/test-dep")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["user_id"] == "test-mock-user"
        assert "tester" in body["data"]["roles"]
        self.app.dependency_overrides.clear()
