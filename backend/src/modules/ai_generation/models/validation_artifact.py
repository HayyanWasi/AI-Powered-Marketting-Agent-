"""Validation artifact model for AI Generation Engine."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..constants import SeverityLevel


@dataclass
class ValidationError:
    """Individual validation error."""

    code: str
    message: str
    severity: SeverityLevel
    field: str | None = None
    suggested_fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "field": self.field,
            "suggested_fix": self.suggested_fix,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationError":
        """Deserialize error from dictionary."""
        return cls(
            code=data["code"],
            message=data["message"],
            severity=SeverityLevel(data["severity"]),
            field=data.get("field"),
            suggested_fix=data.get("suggested_fix"),
        )


@dataclass
class ValidationWarning:
    """Individual validation warning."""

    code: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize warning to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationWarning":
        """Deserialize warning from dictionary."""
        return cls(
            code=data["code"],
            message=data["message"],
            field=data.get("field"),
        )


@dataclass
class ValidationResults:
    """Validation outcome tracking."""

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationWarning] = field(default_factory=list)
    compliance_scores: dict[str, float] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize results to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "compliance_scores": self.compliance_scores,
            "recommendations": self.recommendations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationResults":
        """Deserialize results from dictionary."""
        return cls(
            is_valid=data["is_valid"],
            errors=[ValidationError.from_dict(e) for e in data["errors"]],
            warnings=[ValidationWarning.from_dict(w) for w in data["warnings"]],
            compliance_scores=data["compliance_scores"],
            recommendations=data["recommendations"],
        )


@dataclass
class ValidationArtifact:
    """Validation results describing compliance with business rules and platform requirements."""

    id: str
    generated_at: datetime
    artifact_type: str
    artifact_id: str
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationWarning] = field(default_factory=list)
    compliance_scores: dict[str, float] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    validated_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize artifact to dictionary."""
        return {
            "id": self.id,
            "generated_at": self.generated_at.isoformat(),
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "compliance_scores": self.compliance_scores,
            "recommendations": self.recommendations,
            "validated_by": self.validated_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationArtifact":
        """Deserialize artifact from dictionary."""
        return cls(
            id=data["id"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            artifact_type=data["artifact_type"],
            artifact_id=data["artifact_id"],
            is_valid=data["is_valid"],
            errors=[ValidationError.from_dict(e) for e in data["errors"]],
            warnings=[ValidationWarning.from_dict(w) for w in data["warnings"]],
            compliance_scores=data["compliance_scores"],
            recommendations=data["recommendations"],
            validated_by=data.get("validated_by"),
        )

    def is_success(self) -> bool:
        """Check if validation was successful (no errors)."""
        return self.is_valid and len(self.errors) == 0

    def get_error_count(self) -> int:
        """Get total number of errors."""
        return len(self.errors)

    def get_warning_count(self) -> int:
        """Get total number of warnings."""
        return len(self.warnings)

    def get_error_codes(self) -> list[str]:
        """Get list of unique error codes."""
        return list(set(e.code for e in self.errors))

    def get_field_errors(self, field: str) -> list[ValidationError]:
        """Get all errors for a specific field."""
        return [e for e in self.errors if e.field == field]

    def has_errors_for_field(self, field: str) -> bool:
        """Check if there are errors for a specific field."""
        return any(e.field == field for e in self.errors)
