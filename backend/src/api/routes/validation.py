"""API routes for campaign content validation."""

import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.gateways.validation_gateway import ValidationGateway
from src.models.errors import ErrorCode, create_error_response
from src.models.platform import Platform
from src.models.validation import ValidationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["validation"])

validation_gateway = ValidationGateway()


class ValidateCampaignRequest(BaseModel):
    """Request payload for campaign validation."""

    text_content: str = Field(..., min_length=1, description="Campaign text content")
    platform: Platform = Field(..., description="Target social media platform")
    image_url: str | None = Field(default=None, description="Optional campaign image URL")


class PreviewCheckResponse(BaseModel):
    """Response for preview eligibility check."""

    campaign_id: str
    can_preview: bool
    status: str
    message: str


@router.post(
    "/{campaign_id}/validate",
    response_model=ValidationResponse,
    status_code=200,
)
async def validate_campaign(
    campaign_id: str,
    request: ValidateCampaignRequest,
) -> ValidationResponse:
    """
    Validate campaign content against platform requirements.

    Checks character limits (text) and image resolution (if image provided).
    Returns detailed validation results with specific rule violations.

    Args:
        campaign_id: Unique campaign identifier
        request: Validation request with text content, platform, and optional image

    Returns:
        ValidationResponse with text and image validation results

    Raises:
        HTTPException: 400 for invalid input, 500 for internal errors
    """
    try:
        logger.info("Validating campaign %s for %s", campaign_id, request.platform.value)

        response = await validation_gateway.validate_campaign(
            campaign_id=campaign_id,
            text_content=request.text_content,
            platform=request.platform.value,
            image_url=request.image_url,
        )

        logger.info(
            "Campaign %s validation: status=%s, can_preview=%s",
            campaign_id,
            response.status.value,
            response.can_preview,
        )

        return response

    except ValueError as e:
        logger.error("Validation error for campaign %s: %s", campaign_id, e)
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid validation request: {e}",
            ).model_dump(),
        )
    except Exception as e:
        logger.exception("Unexpected error validating campaign %s: %s", campaign_id, e)
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred during validation",
                details={"request_id": str(uuid.uuid4())},
            ).model_dump(),
        )


@router.get(
    "/{campaign_id}/preview/check",
    response_model=PreviewCheckResponse,
    status_code=200,
)
async def check_preview_eligibility(
    campaign_id: str,
    text_content: str,
    platform: Platform,
    image_url: str | None = None,
) -> PreviewCheckResponse:
    """
    Check if a campaign is eligible for preview based on validation.

    Quick check that returns whether the campaign passes all validation
    rules and can proceed to human review.

    Args:
        campaign_id: Unique campaign identifier
        text_content: Campaign text to validate
        platform: Target platform
        image_url: Optional image URL

    Returns:
        PreviewCheckResponse with eligibility status
    """
    try:
        logger.info("Checking preview eligibility for campaign %s", campaign_id)

        response = await validation_gateway.validate_campaign(
            campaign_id=campaign_id,
            text_content=text_content,
            platform=platform.value,
            image_url=image_url,
        )

        can_preview = validation_gateway.can_preview(response)

        if can_preview:
            message = "Campaign passed all validation rules and is eligible for preview"
        else:
            violation_count = len(response.text_validation.violations) + len(
                response.image_validation.violations
            )
            message = (
                f"Campaign failed validation with {violation_count} rule violation(s). "
                "Fix the issues and try again."
            )

        return PreviewCheckResponse(
            campaign_id=campaign_id,
            can_preview=can_preview,
            status=response.status.value,
            message=message,
        )

    except Exception as e:
        logger.exception("Error checking preview for campaign %s: %s", campaign_id, e)
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred during preview check",
                details={"request_id": str(uuid.uuid4())},
            ).model_dump(),
        )
