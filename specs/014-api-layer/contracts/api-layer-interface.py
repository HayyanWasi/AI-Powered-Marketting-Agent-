"""API Layer — public contract for the API infrastructure.

The API layer is a cross-cutting infrastructure module that exposes
business module functionality through REST endpoints. It handles
routing, validation, authentication, error translation, and documentation
while delegating all business logic to the appropriate modules.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# ─── Response Models ───────────────────────────────────────────────


class APIResponse:
    """Standardized JSON envelope for successful responses."""

    def __init__(self, data: Any, message: str = "OK") -> None:
        self.status: str = "success"
        self.data: Any = data
        self.message: str = message
        self.timestamp: str = datetime.utcnow().isoformat() + "Z"


class APIErrorResponse:
    """Standardized JSON envelope for error responses."""

    def __init__(
        self,
        error: str,
        message: str,
        status_code: int = 500,
        details: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        self.status: str = "error"
        self.error: str = error
        self.message: str = message
        self.details: Optional[List[Dict[str, str]]] = details
        self.timestamp: str = datetime.utcnow().isoformat() + "Z"
        self.status_code: int = status_code


class ValidationErrorDetail:
    """A single structured validation error detail."""

    def __init__(self, field: str, message: str, code: str) -> None:
        self.field: str = field
        self.message: str = message
        self.code: str = code


# ─── Auth Contract ─────────────────────────────────────────────────


class AuthenticatedUser:
    """Resolved user identity from authentication token."""

    def __init__(
        self,
        id: str,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
    ) -> None:
        self.id: str = id
        self.roles: List[str] = roles or []
        self.permissions: List[str] = permissions or []


class AuthenticationProvider(ABC):
    """Contract for authentication dependency.

    Implementations validate credentials and return an AuthenticatedUser.
    The API layer does not implement authentication logic; it delegates
    to this contract.
    """

    @abstractmethod
    async def authenticate(self, token: str) -> AuthenticatedUser:
        """Validate credentials and return the authenticated user.

        Args:
            token: Bearer token from Authorization header.

        Returns:
            AuthenticatedUser with resolved identity.

        Raises:
            UnauthorizedError: If token is invalid or expired.
        """
        ...

    @abstractmethod
    async def authorize(self, user: AuthenticatedUser, resource: str, action: str) -> bool:
        """Check if user is authorized to perform action on resource.

        Args:
            user: Authenticated user identity.
            resource: Resource identifier being accessed.
            action: Action to perform (e.g., "read", "write", "delete").

        Returns:
            True if authorized, False otherwise.

        Raises:
            ForbiddenError: If user lacks required permissions.
        """
        ...


# ─── Exception Translation Contract ────────────────────────────────


class ErrorType(str, Enum):
    """Machine-readable error type identifiers."""

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"
    BAD_REQUEST = "bad_request"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    NOT_ACCEPTABLE = "not_acceptable"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    URI_TOO_LONG = "uri_too_long"


class ExceptionHandler(ABC):
    """Contract for exception-to-HTTP response translation."""

    @abstractmethod
    def handle(self, exc: Exception) -> APIErrorResponse:
        """Translate an exception to a standardized error response.

        Args:
            exc: The exception to translate.

        Returns:
            APIErrorResponse with appropriate status code and message.
        """
        ...


# ─── Middleware Contract ────────────────────────────────────────────


class MiddlewareProvider(ABC):
    """Contract for API middleware configuration."""

    @abstractmethod
    def get_cors_origins(self) -> List[str]:
        """Return allowed CORS origins."""
        ...

    @abstractmethod
    def get_security_headers(self) -> Dict[str, str]:
        """Return security headers to include in all responses."""
        ...

    @abstractmethod
    def is_rate_limited(self, client_id: str) -> bool:
        """Check if a client has exceeded rate limits.

        Args:
            client_id: Client identifier (IP or user ID).

        Returns:
            True if rate limited, False otherwise.
        """
        ...


# ─── API Version Configuration ─────────────────────────────────────


class APIVersion:
    """Configuration for a single API version."""

    def __init__(
        self,
        version: str,
        prefix: str,
        is_active: bool = True,
        deprecation_date: Optional[datetime] = None,
    ) -> None:
        self.version: str = version
        self.prefix: str = prefix
        self.is_active: bool = is_active
        self.deprecation_date: Optional[datetime] = deprecation_date


# ─── Public API Endpoints (Route Contracts) ────────────────────────

# Note: These are exemplar endpoint contracts. Actual implementations
# will be in routers under backend/src/api/v1/ and backend/src/api/v2/.
# Each router delegates to its corresponding business module.

HEALTH_ENDPOINTS = {
    "GET /health": "Basic health check (returns OK)",
    "GET /ready": "Readiness check (dependencies available)",
    "GET /live": "Liveness check (process alive)",
}

API_CONTRACTS = {
    "Health": {
        "prefix": "/api/v1",
        "endpoints": {
            "GET /health": "Return API status",
            "GET /ready": "Return readiness status",
            "GET /live": "Return liveness status",
        },
    },
    "Campaigns": {
        "prefix": "/api/v1/campaigns",
        "endpoints": {
            "POST /": "Create a new campaign",
            "GET /": "List campaigns with pagination",
            "GET /{id}": "Get campaign by ID",
            "PUT /{id}": "Update campaign",
            "DELETE /{id}": "Delete campaign",
        },
    },
    "Company": {
        "prefix": "/api/v1/company",
        "endpoints": {
            "GET /profile": "Get company profile",
            "PUT /profile": "Update company profile",
            "POST /brand-image": "Upload brand reference image",
        },
    },
    "Guest Info": {
        "prefix": "/api/v1/guest",
        "endpoints": {
            "POST /search": "Search for guest/company information",
        },
    },
    "AI Generation": {
        "prefix": "/api/v1/generate",
        "endpoints": {
            "POST /copy": "Generate marketing copy",
            "POST /image": "Generate campaign image",
            "POST /strategy": "Generate campaign strategy",
        },
    },
    "Workflow": {
        "prefix": "/api/v1/workflows",
        "endpoints": {
            "POST /": "Start a workflow execution",
            "GET /{id}": "Get workflow status",
            "POST /{id}/approve": "Approve workflow step",
            "POST /{id}/reject": "Reject workflow step",
        },
    },
}
