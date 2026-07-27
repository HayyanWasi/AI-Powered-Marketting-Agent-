"""Validation service that coordinates text and image validation for campaigns."""

import logging
from dataclasses import dataclass

from src.models.platform import Platform
from src.models.validation import (
    ImageValidationResultInternal,
    RuleSeverity,
    RuleViolation,
    ValidationRequest,
    ValidationResultInternal,
    ValidationStatus,
)
from src.services.image_validation_service import ImageValidationService
from src.validators.text_validator import validate_text_content

logger = logging.getLogger(__name__)


@dataclass
class ValidationError(Exception):
    """Validation service error."""

    message: str
    details: dict | None = None


class ValidationService:
    """Service for validating campaign content against platform requirements.

    Coordinates text validation (character limits) and image validation
    (resolution, accessibility) into a single validation result.
    """

    def __init__(self, image_validation_service: ImageValidationService | None = None):
        self._image_service = image_validation_service or ImageValidationService()

    async def validate(self, request: ValidationRequest) -> ValidationResultInternal:
        """
        Validate campaign content against platform rules.

        Runs text and image validation independently, combining results
        into a single ValidationResponse.

        Args:
            request: ValidationRequest with campaign content and platform

        Returns:
            ValidationResultInternal with combined text and image results

        Raises:
            ValidationError: If validation cannot be performed
        """
        logger.info(
            "Starting validation for campaign %s on %s",
            request.campaign_id,
            request.platform.value,
        )

        # Text validation (synchronous, no external calls)
        text_result = validate_text_content(request.text_content, request.platform)

        # Image validation (async, HTTP calls)
        image_result = await self._validate_image(request.image_url, request.platform)

        # Determine overall status
        overall_status = self._determine_status(text_result, image_result)

        result = ValidationResultInternal(
            campaign_id=request.campaign_id,
            platform=request.platform,
            status=overall_status,
            text_result=text_result,
            image_result=image_result,
        )

        logger.info(
            "Validation complete for campaign %s: status=%s, can_preview=%s",
            request.campaign_id,
            overall_status.value,
            result.to_response().can_preview,
        )

        return result

    async def _validate_image(
        self,
        image_url: str | None,
        platform: Platform,
    ) -> ImageValidationResultInternal:
        """Validate image if provided, otherwise return pass with no data."""
        if not image_url:
            logger.debug("No image URL provided, skipping image validation")
            return ImageValidationResultInternal(
                passed=True,
                width=0,
                height=0,
                content_type="",
                violations=[],
            )

        try:
            async with self._image_service as service:
                raw_result = await service.validate_image_url(image_url)

            violations: list[RuleViolation] = []

            if not raw_result.is_valid:
                for error_msg in raw_result.errors:
                    violation = RuleViolation(
                        rule_id="IMG_VALIDATION",
                        rule_name="Image Validation",
                        message=error_msg,
                        severity=RuleSeverity.ERROR,
                    )
                    violations.append(violation)

            return ImageValidationResultInternal(
                passed=raw_result.is_valid,
                width=raw_result.width,
                height=raw_result.height,
                content_type=raw_result.content_type,
                violations=violations,
            )

        except Exception as e:
            logger.error("Image validation failed: %s", e)
            return ImageValidationResultInternal(
                passed=False,
                width=0,
                height=0,
                content_type="",
                violations=[
                    RuleViolation(
                        rule_id="IMG_VALIDATION_ERROR",
                        rule_name="Image Validation Error",
                        message=f"Image validation could not be performed: {e}",
                        severity=RuleSeverity.ERROR,
                    )
                ],
            )

    def _determine_status(
        self,
        text_result: "TextValidationResultInternal",
        image_result: "ImageValidationResultInternal",
    ) -> ValidationStatus:
        """Determine overall validation status from text and image results."""
        has_errors = (
            not text_result.passed
            or any(v.severity == RuleSeverity.ERROR for v in text_result.violations)
            or not image_result.passed
            or any(v.severity == RuleSeverity.ERROR for v in image_result.violations)
        )

        has_warnings = any(
            v.severity == RuleSeverity.WARNING
            for v in text_result.violations + image_result.violations
        )

        if has_errors:
            return ValidationStatus.FAIL
        if has_warnings:
            return ValidationStatus.WARNING
        return ValidationStatus.PASS
