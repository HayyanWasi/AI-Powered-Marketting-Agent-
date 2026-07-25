"""Dependency injection entry points for the API layer.

Provides FastAPI `Depends()` callables for:
- Authentication (token validation)
- Authorization (permission checks)
- Business module service injection

All dependencies are wired via FastAPI's dependency injection system
so that route handlers never instantiate services directly.
"""

from uuid import UUID


class AuthenticatedUser:
    """Resolved user identity from authentication token.

    Attached to the request scope via the auth dependency.
    """

    def __init__(self, id: str, roles: list[str] | None = None, permissions: list[str] | None = None) -> None:
        self.id = id
        self.roles = roles or []
        self.permissions = permissions or []


async def get_authenticated_user() -> AuthenticatedUser:
    """Authenticate the current request and return user identity.

    For MVP: Returns a placeholder authenticated user.
    In production, this validates JWT/OAuth2 tokens via an Auth module.

    Returns:
        AuthenticatedUser with resolved identity.

    Raises:
        HTTPException 401: If authentication fails.
    """
    return AuthenticatedUser(
        id="00000000-0000-0000-0000-000000000001",
        roles=["admin"],
        permissions=["read", "write", "delete"],
    )


async def require_permission(resource: str, action: str) -> None:
    """Dependency factory that checks user permissions.

    Usage:
        @router.get("/campaigns/{id}")
        async def get_campaign(
            campaign_id: UUID,
            user: AuthenticatedUser = Depends(get_authenticated_user),
            _: None = Depends(require_permission("campaigns", "read")),
        ):
            ...

    For MVP: Permissive — allows all actions for authenticated users.
    In production, this checks user.roles/permissions against a policy.
    """

    async def _check() -> None:
        pass

    return _check
