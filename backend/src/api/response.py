"""Standardized API response envelope models."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Standardized JSON envelope for successful responses."""

    status: str = "success"
    data: Any = None
    message: str = "OK"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))


class ValidationErrorDetail(BaseModel):
    """A single structured validation error detail."""

    field: str
    message: str
    code: str


class APIErrorResponse(BaseModel):
    """Standardized JSON envelope for error responses."""

    status: str = "error"
    error: str = "internal_error"
    message: str = "An unexpected error occurred"
    details: Optional[List[ValidationErrorDetail]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))


def success_response(data: Any = None, message: str = "OK") -> APIResponse:
    """Build a standardized success response envelope.

    Args:
        data: Response payload.
        message: Human-readable status message.

    Returns:
        APIResponse with current timestamp.
    """
    return APIResponse(data=data, message=message)


def error_response(
    error: str = "internal_error",
    message: str = "An unexpected error occurred",
    details: Optional[List[ValidationErrorDetail]] = None,
) -> APIErrorResponse:
    """Build a standardized error response envelope.

    Args:
        error: Machine-readable error type identifier.
        message: Human-readable error description.
        details: Structured validation error details.

    Returns:
        APIErrorResponse with current timestamp.
    """
    return APIErrorResponse(error=error, message=message, details=details)
