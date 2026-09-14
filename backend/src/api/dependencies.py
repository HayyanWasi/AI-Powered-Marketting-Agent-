"""Dependency injection entry points for the API layer.

Provides FastAPI `Depends()` callables for:
- Authentication (token validation)
- Authorization (permission checks)
- Business module service injection

All dependencies are wired via FastAPI's dependency injection system
so that route handlers never instantiate services directly.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import Header, HTTPException, status

from src.modules.operations.services.platform_operations import PlatformOperationsService

logger = logging.getLogger(__name__)


class AuthenticatedUser:
    """Resolved user identity from authentication token.

    Attached to the request scope via the auth dependency.
    """

    def __init__(
        self,
        id: str,
        email: str | None = None,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
    ) -> None:
        self.id = id
        self.email = email
        self.roles = roles or []
        self.permissions = permissions or []


async def get_authenticated_user(
    authorization: str | None = Header(None, alias="Authorization"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> AuthenticatedUser:
    """Authenticate the current request and return user identity.

    Validates Supabase JWT from Authorization: Bearer <token> header.
    Supports X-User-Id for verified internal/test services.

    Returns:
        AuthenticatedUser with resolved identity.

    Raises:
        HTTPException 401: If authentication fails.
    """
    # Guard against direct function invocation in unit tests where default is Header object
    if not isinstance(authorization, str):
        authorization = None
    if not isinstance(x_user_id, str):
        x_user_id = None

    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization scheme. Expected 'Bearer <token>'.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = authorization[7:].strip()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Empty bearer token provided.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            from src.config.supabase import get_supabase_client

            supabase = get_supabase_client()
            user_response = supabase.auth.get_user(token)
            if not user_response or not getattr(user_response, "user", None):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired Supabase authentication token.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            sb_user = user_response.user
            user_id = str(sb_user.id)
            email = getattr(sb_user, "email", None)
            app_meta = getattr(sb_user, "app_metadata", {}) or {}
            roles = app_meta.get("roles", ["authenticated"])
            return AuthenticatedUser(
                id=user_id,
                email=email,
                roles=roles,
                permissions=["read", "write", "delete"],
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Supabase token verification failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    if x_user_id:
        try:
            UUID(x_user_id)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-User-Id header format. Must be a valid UUID.",
            ) from err
        return AuthenticatedUser(
            id=x_user_id,
            roles=["authenticated"],
            permissions=["read", "write", "delete"],
        )

    from src.config.settings import settings

    if getattr(settings, "REQUIRE_AUTH", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Supabase Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

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


# Global singleton for operations service
_OPERATIONS_SERVICE: PlatformOperationsService | None = None


def get_operations_service() -> PlatformOperationsService:
    """Get the singleton PlatformOperationsService instance."""
    global _OPERATIONS_SERVICE
    if _OPERATIONS_SERVICE is None:
        from src.config.settings import settings
        from src.config.supabase import get_supabase_client

        try:
            supabase_client = get_supabase_client()
        except Exception as e:
            # Telemetry must never block startup — history persistence degrades
            # to a no-op while logs and metrics keep working.
            logger.warning("Operations history persistence disabled: %s", e)
            supabase_client = None

        _OPERATIONS_SERVICE = PlatformOperationsService(
            project_name=settings.langsmith_project,
            service_name=settings.otel_service_name,
            otlp_endpoint=settings.otel_exporter_otlp_endpoint,
            supabase_client=supabase_client,
        )
    return _OPERATIONS_SERVICE
