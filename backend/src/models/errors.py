"""Custom exception classes for the Campaign Management module."""

from enum import Enum
from typing import Any, Optional, List

from fastapi import HTTPException, status
from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Error codes for API responses."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"
    STATE_TRANSITION_INVALID = "STATE_TRANSITION_INVALID"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    DUPLICATE_NAME = "DUPLICATE_NAME"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    message: str
    details: dict[str, Any] | None = None


class ValidationErrorDetail(BaseModel):
    """Detail for validation errors."""

    field: str
    message: str


def create_error_response(
    error_code: ErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
) -> ErrorResponse:
    """Create a standardized error response."""
    return ErrorResponse(
        error=error_code.value,
        message=message,
        details=details,
    )


class CampaignError(HTTPException):
    """Base exception for campaign errors."""

    def __init__(self, detail: str, code: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail={"detail": detail, "code": code})


class NotFoundError(CampaignError):
    """Resource not found."""

    def __init__(self, resource: str = "Campaign", resource_id: str = ""):
        detail = f"{resource} not found"
        if resource_id:
            detail += f": {resource_id}"
        super().__init__(detail=detail, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)


class ValidationError(CampaignError):
    """Validation error with field details."""

    def __init__(self, detail: str, invalid_fields: Optional[List[str]] = None):
        super().__init__(
            detail=detail, code="VALIDATION_ERROR", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        self.invalid_fields = invalid_fields or []


class StateTransitionError(CampaignError):
    """Invalid state transition attempted."""

    def __init__(self, current_state: str, attempted_state: str, valid_states: List[str]):
        detail = (
            f"Cannot transition from '{current_state}' to '{attempted_state}'. "
            f"Valid next states: {', '.join(valid_states)}"
        )
        super().__init__(
            detail=detail, code="STATE_TRANSITION_INVALID", status_code=status.HTTP_409_CONFLICT
        )
        self.current_state = current_state
        self.attempted_state = attempted_state
        self.valid_states = valid_states


class VersionConflictError(CampaignError):
    """Optimistic locking version conflict."""

    def __init__(self, expected_version: int, actual_version: int):
        detail = f"Version conflict: expected {expected_version}, found {actual_version}"
        super().__init__(
            detail=detail, code="VERSION_CONFLICT", status_code=status.HTTP_409_CONFLICT
        )
        self.expected_version = expected_version
        self.actual_version = actual_version


class DuplicateNameError(CampaignError):
    """Duplicate campaign name within organization."""

    def __init__(self, name: str):
        detail = f"Campaign with name '{name}' already exists in this organization"
        super().__init__(detail=detail, code="DUPLICATE_NAME", status_code=status.HTTP_409_CONFLICT)


class PreconditionFailedError(CampaignError):
    """Required precondition not met for operation."""

    def __init__(self, detail: str):
        super().__init__(
            detail=detail, code="PRECONDITION_FAILED", status_code=status.HTTP_409_CONFLICT
        )
