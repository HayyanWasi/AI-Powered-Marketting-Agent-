"""Unit tests for API authentication and authorization dependencies."""


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
    async def test_returns_authenticated_user(self) -> None:
        user = await get_authenticated_user()
        assert isinstance(user, AuthenticatedUser)
        assert user.id is not None
        assert len(user.roles) > 0


class TestRequirePermission:
    async def test_permission_check_returns_none(self) -> None:
        checker = await require_permission("campaigns", "read")
        result = await checker()
        assert result is None
