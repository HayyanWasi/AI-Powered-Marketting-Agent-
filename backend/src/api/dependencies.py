"""Dependency injection entry points for the API layer.

Provides FastAPI `Depends()` callables for:
- Authentication (token validation)
- Authorization (permission checks)
- Business module service injection

All dependencies are wired via FastAPI's dependency injection system
so that route handlers never instantiate services directly.
"""

import logging


class AuthenticatedUser:
    """Resolved user identity from authentication token.

    Attached to the request scope via the auth dependency.
    """

    def __init__(
        self, id: str, roles: list[str] | None = None, permissions: list[str] | None = None
    ) -> None:
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


from src.modules.operations.services.platform_operations import PlatformOperationsService

logger = logging.getLogger(__name__)

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
