"""Unit tests for API authentication and authorization dependencies."""

import pytest
from fastapi import HTTPException

from src.api.dependencies import AuthenticatedUser, get_authenticated_user, require_permission


class TestAuthenticatedUser:
    def test_default_roles_and_permissions(self) -> None:
        user = AuthenticatedUser(id="user-1")
        assert user.id == "user-1"
        assert user.roles == []
        assert user.permissions == []

    def test_with_roles_and_permissions(self) -> None:
        user = AuthenticatedUser(id="user-1", roles=["admin"], permissions=["read", "write"])
        assert "admin" in user.roles
        assert "read" in user.permissions


class TestGetAuthenticatedUser:
    async def test_returns_authenticated_user_with_id_when_auth_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.config.settings import settings

        monkeypatch.setattr(settings, "REQUIRE_AUTH", False)
        user = await get_authenticated_user(x_user_id="00000000-0000-0000-0000-000000000001")
        assert isinstance(user, AuthenticatedUser)
        assert user.id == "00000000-0000-0000-0000-000000000001"
        assert len(user.roles) > 0

    async def test_x_user_id_cannot_bypass_auth_when_required(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.config.settings import settings

        monkeypatch.setattr(settings, "REQUIRE_AUTH", True)
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_user(x_user_id="00000000-0000-0000-0000-000000000001")
        assert exc_info.value.status_code == 401

    async def test_unauthenticated_raises_401(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_user(authorization=None, x_user_id=None)
        assert exc_info.value.status_code == 401

    async def test_expired_token_raises_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import MagicMock

        from src.config.settings import settings

        monkeypatch.setattr(settings, "REQUIRE_AUTH", True)
        mock_client = MagicMock()
        mock_client.auth.get_user.side_effect = Exception("Token is expired")
        monkeypatch.setattr("src.config.supabase.get_supabase_client", lambda: mock_client)

        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_user(authorization="Bearer expired-token-jwt")
        assert exc_info.value.status_code == 401
        assert (
            "Token verification failed" in exc_info.value.detail
            or "expired" in exc_info.value.detail.lower()
        )

    async def test_expired_token_null_user_raises_401(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from unittest.mock import MagicMock

        from src.config.settings import settings

        monkeypatch.setattr(settings, "REQUIRE_AUTH", True)
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = None
        monkeypatch.setattr("src.config.supabase.get_supabase_client", lambda: mock_client)

        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_user(authorization="Bearer expired-token-jwt")
        assert exc_info.value.status_code == 401
        assert (
            "expired" in exc_info.value.detail.lower() or "invalid" in exc_info.value.detail.lower()
        )


class TestRequirePermission:
    async def test_permission_check_returns_none(self) -> None:
        checker = await require_permission("campaigns", "read")
        result = await checker()
        assert result is None
