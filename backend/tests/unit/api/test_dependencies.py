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
    async def test_returns_authenticated_user_with_id(self) -> None:
        user = await get_authenticated_user(x_user_id="00000000-0000-0000-0000-000000000001")
        assert isinstance(user, AuthenticatedUser)
        assert user.id == "00000000-0000-0000-0000-000000000001"
        assert len(user.roles) > 0

    async def test_unauthenticated_raises_401(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_user(authorization=None, x_user_id=None)
        assert exc_info.value.status_code == 401


class TestRequirePermission:
    async def test_permission_check_returns_none(self) -> None:
        checker = await require_permission("campaigns", "read")
        result = await checker()
        assert result is None
