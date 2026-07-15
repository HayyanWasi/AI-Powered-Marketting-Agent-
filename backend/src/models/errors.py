from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Standardized error codes for the API."""

    VALIDATION_ERROR = "validation_error"
    PROFILE_NOT_FOUND = "profile_not_found"
    VALIDATION_FAILED = "validation_failed"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"


class ErrorResponse(BaseModel):
    """Standardized error response envelope."""

    error: ErrorCode = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error context",
    )


class ValidationErrorDetail(BaseModel):
    """Detail for validation errors."""

    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")


def create_error_response(
    error_code: ErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
) -> ErrorResponse:
    """Create a standardized error response."""
    return ErrorResponse(
        error=error_code,
        message=message,
        details=details,
    )
