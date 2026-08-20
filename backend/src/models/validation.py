from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.models.platform import Platform


class ValidationStatus(str, Enum):
    """Overall validation status."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class RuleSeverity(str, Enum):
    """Severity of a validation rule violation."""

    ERROR = "error"
    WARNING = "warning"


class ValidationRequest(BaseModel):
    """Request payload for campaign validation."""

    campaign_id: str = Field(..., description="ID of the campaign to validate")
    text_content: str = Field(..., description="Campaign text content to validate")
    image_url: str | None = Field(default=None, description="URL of campaign image to validate")
    platform: Platform = Field(..., description="Target social media platform")


class RuleViolation(BaseModel):
    """A single validation rule violation."""

    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    message: str = Field(..., description="Error message describing the violation")
    severity: RuleSeverity = Field(..., description="Severity of the violation")
    current_value: Any = Field(default=None, description="Value that violated the rule")
    expected_value: Any = Field(default=None, description="Expected value or constraint")


class TextValidationResult(BaseModel):
    """Result of text content validation."""

    passed: bool = Field(..., description="Whether text validation passed")
    character_count: int = Field(..., description="Total character count")
    character_limit: int = Field(..., description="Platform character limit")
    violations: list[RuleViolation] = Field(
        default_factory=list, description="Text rule violations"
    )


class ImageValidationResult(BaseModel):
    """Result of image validation."""

    passed: bool = Field(..., description="Whether image validation passed")
    width: int = Field(default=0, description="Image width in pixels")
    height: int = Field(default=0, description="Image height in pixels")
    content_type: str = Field(default="", description="Image content type")
    violations: list[RuleViolation] = Field(
        default_factory=list, description="Image rule violations"
    )


class ValidationResponse(BaseModel):
    """Response payload for campaign validation."""

    campaign_id: str = Field(..., description="ID of the validated campaign")
    platform: Platform = Field(..., description="Platform validated against")
    status: ValidationStatus = Field(..., description="Overall validation status")
    text_validation: TextValidationResult = Field(..., description="Text validation results")
    image_validation: ImageValidationResult = Field(
        default=..., description="Image validation results"
    )
    validated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Timestamp of validation",
    )
    can_preview: bool = Field(..., description="Whether campaign can proceed to preview")


@dataclass
class ValidationResultInternal:
    """Internal validation result dataclass."""

    campaign_id: str = ""
    platform: Platform = Platform.LINKEDIN
    status: ValidationStatus = ValidationStatus.PASS
    text_result: "TextValidationResultInternal" = field(
        default_factory=lambda: TextValidationResultInternal()
    )
    image_result: "ImageValidationResultInternal" = field(
        default_factory=lambda: ImageValidationResultInternal()
    )
    validated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_response(self) -> ValidationResponse:
        return ValidationResponse(
            campaign_id=self.campaign_id,
            platform=self.platform,
            status=self.status,
            text_validation=self.text_result.to_model(),
            image_validation=self.image_result.to_model(),
            validated_at=self.validated_at,
            can_preview=self.status == ValidationStatus.PASS,
        )


@dataclass
class TextValidationResultInternal:
    """Internal text validation result."""

    passed: bool = True
    character_count: int = 0
    character_limit: int = 0
    violations: list[RuleViolation] = field(default_factory=list)

    def to_model(self) -> TextValidationResult:
        return TextValidationResult(
            passed=self.passed,
            character_count=self.character_count,
            character_limit=self.character_limit,
            violations=self.violations,
        )


@dataclass
class ImageValidationResultInternal:
    """Internal image validation result."""

    passed: bool = True
    width: int = 0
    height: int = 0
    content_type: str = ""
    violations: list[RuleViolation] = field(default_factory=list)

    def to_model(self) -> ImageValidationResult:
        return ImageValidationResult(
            passed=self.passed,
            width=self.width,
            height=self.height,
            content_type=self.content_type,
            violations=self.violations,
        )
