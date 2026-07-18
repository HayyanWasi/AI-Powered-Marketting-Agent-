"""Validation gateway that orchestrates the full validation pipeline."""

import logging
import uuid

from src.models.validation import (
    ValidationRequest,
    ValidationResponse,
    ValidationResultInternal,
)
from src.services.validation_service import ValidationService

logger = logging.getLogger(__name__)


class ValidationGateway:
    """Gateway for orchestrating campaign validation.

    Entry point for the validation pipeline. Coordinates validation
    service execution and provides a clean API boundary for the
    validation process.
    """

    def __init__(self, validation_service: ValidationService | None = None):
        self._service = validation_service or ValidationService()

    async def validate_campaign(
        self,
        campaign_id: str,
        text_content: str,
        platform: str,
        image_url: str | None = None,
    ) -> ValidationResponse:
        """
        Validate a campaign and return the full validation response.

        Args:
            campaign_id: Unique identifier for the campaign
            text_content: Campaign text to validate
            platform: Target platform (linkedin, instagram, facebook)
            image_url: Optional image URL to validate

        Returns:
            ValidationResponse with combined text and image validation results
        """
        from src.models.platform import Platform

        logger.info("Validation gateway: validating campaign %s", campaign_id)

        platform_enum = Platform(platform.lower())

        request = ValidationRequest(
            campaign_id=campaign_id,
            text_content=text_content,
            image_url=image_url,
            platform=platform_enum,
        )

        result: ValidationResultInternal = await self._service.validate(request)
        response = result.to_response()

        logger.info(
            "Validation gateway: campaign %s status=%s, can_preview=%s",
            campaign_id,
            response.status.value,
            response.can_preview,
        )

        return response

    def can_preview(self, validation_response: ValidationResponse) -> bool:
        """
        Check if a campaign can proceed to preview based on validation results.

        Args:
            validation_response: The validation response to check

        Returns:
            True if campaign can proceed to preview, False otherwise
        """
        return validation_response.can_preview
