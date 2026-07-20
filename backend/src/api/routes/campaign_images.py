import logging
import time
import uuid

from fastapi import APIRouter, HTTPException

from src.models.brand_style import BrandStyleContextInternal, PollinationsPrompt
from src.models.campaign_image import (
    CampaignImageRequest,
    CampaignImageResponse,
    ValidationResult,
)
from src.models.errors import ErrorCode, create_error_response
from src.services.brand_style_service import BrandStyleService
from src.services.company_profile_service import CompanyProfileNotFoundError, CompanyProfileService
from src.services.image_validation_service import ImageValidationService
from src.services.pollinations_service import (
    PollinationsRateLimitError,
    PollinationsServerError,
    PollinationsService,
    PollinationsServiceError,
    PollinationsTimeoutError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaign-images", tags=["campaign-images"])

# Initialize services
company_profile_service = CompanyProfileService()
brand_style_service = BrandStyleService()


def _is_brand_applied(brand_context: BrandStyleContextInternal) -> bool:
    """Check if any brand data was used during generation."""
    return brand_context is not None and (
        brand_context.color_palette is not None
        or brand_context.personality_descriptors is not None
        or brand_context.style_guidance is not None
        or brand_context.logo_reference is not None
        or len(brand_context.reference_image_urls) > 0
    )


def _make_validation(width: int, height: int, passed: bool) -> ValidationResult:
    """Create a ValidationResult for the response."""
    return ValidationResult(width=width, height=height, passed=passed)


@router.post("", response_model=CampaignImageResponse, status_code=200)
async def generate_campaign_image(request: CampaignImageRequest) -> CampaignImageResponse:
    """
    Generate a brand-styled campaign image using Pollinations AI.

    Args:
        request: Campaign image generation request with company profile ID and prompt

    Returns:
        CampaignImageResponse with image URL and metadata

    Raises:
        HTTPException: 400 for validation errors, 404 for profile not found,
                      422 for validation failure, 503 for service unavailable,
                      500 for internal errors
    """
    start_time = time.monotonic()

    try:
        # 1. Fetch company profile
        logger.info("Fetching company profile: %s", request.company_profile_id)
        profile = await company_profile_service.get_profile(str(request.company_profile_id))

        # 2. Extract brand context
        brand_context = brand_style_service.extract_brand_context(profile)

        # 3. Build Pollinations prompt
        pollinations_prompt = brand_style_service.build_prompt(
            campaign_prompt=request.campaign_prompt,
            brand_context=brand_context,
            campaign_context=request.campaign_context,
        )

        # 4. Generate image with Pollinations
        logger.info("Generating image with Pollinations (model=kontext)")
        async with PollinationsService() as pollinations_service:
            try:
                image_url, generation_time_ms = await pollinations_service.generate_image(
                    prompt=pollinations_prompt.base_prompt,
                    brand_context=brand_context,
                )
            except PollinationsServerError as e:
                logger.warning("Pollinations server error, generating fallback: %s", e)
                async with PollinationsService() as fallback_service:
                    image_url, _ = await fallback_service.generate_fallback(brand_context)
                generation_time_ms = int((time.monotonic() - start_time) * 1000)
                return CampaignImageResponse(
                    image_url=image_url,
                    model="kontext",
                    generation_time_ms=generation_time_ms,
                    fallback_used=True,
                    brand_applied=_is_brand_applied(brand_context),
                    validation=_make_validation(0, 0, False),
                )
            except PollinationsRateLimitError as e:
                logger.warning("Pollinations rate limited: %s", e)
                raise HTTPException(
                    status_code=503,
                    detail=create_error_response(
                        error_code=ErrorCode.SERVICE_UNAVAILABLE,
                        message="Image generation service temporarily unavailable due to rate limiting",
                        details={
                            "retry_after_seconds": e.retry_after or 30,
                            "fallback_available": True,
                        },
                    ).model_dump(),
                )
            except PollinationsTimeoutError as e:
                logger.warning("Pollinations timeout: %s", e)
                raise HTTPException(
                    status_code=503,
                    detail=create_error_response(
                        error_code=ErrorCode.SERVICE_UNAVAILABLE,
                        message="Image generation service timed out",
                        details={"retry_after_seconds": 30, "fallback_available": True},
                    ).model_dump(),
                )
            except PollinationsServiceError as e:
                logger.error("Pollinations service error: %s", e)
                raise HTTPException(
                    status_code=503,
                    detail=create_error_response(
                        error_code=ErrorCode.SERVICE_UNAVAILABLE,
                        message="Image generation service temporarily unavailable",
                        details={"retry_after_seconds": 30, "fallback_available": True},
                    ).model_dump(),
                )

        # 5. Validate generated image
        logger.info("Validating generated image")
        async with ImageValidationService() as validation_service:
            validation_result = await validation_service.validate_image_url(image_url)

        # 6. If validation fails, retry once with adjusted prompt
        if not validation_result.is_valid:
            logger.warning(
                "Image validation failed: %s. Retrying with adjusted prompt.",
                validation_result.errors,
            )
            return await _retry_with_validation(
                pollinations_prompt=pollinations_prompt,
                brand_context=brand_context,
                start_time=start_time,
            )

        # Success case
        generation_time_ms = int((time.monotonic() - start_time) * 1000)
        logger.info("Campaign image generated successfully in %dms", generation_time_ms)

        return CampaignImageResponse(
            image_url=image_url,
            model="kontext",
            generation_time_ms=generation_time_ms,
            fallback_used=False,
            brand_applied=_is_brand_applied(brand_context),
            validation=_make_validation(
                validation_result.width, validation_result.height, validation_result.is_valid
            ),
        )

    except CompanyProfileNotFoundError as e:
        logger.warning("Company profile not found: %s", e.details)
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                error_code=ErrorCode.PROFILE_NOT_FOUND,
                message="Company profile not found",
                details=e.details,
            ).model_dump(),
        )
    except ValueError as e:
        logger.error("Validation error: %s", e)
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="Invalid request parameters",
                details={"field": "campaign_prompt", "message": str(e)},
            ).model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error generating campaign image: %s", e)
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred",
                details={"request_id": str(uuid.uuid4())},
            ).model_dump(),
        )


async def _retry_with_validation(
    pollinations_prompt: PollinationsPrompt,
    brand_context: BrandStyleContextInternal,
    start_time: float,
) -> CampaignImageResponse:
    """Retry image generation with high-resolution hint after validation failure."""
    retry_prompt = f"{pollinations_prompt.base_prompt}, high resolution, 1080p, detailed"
    async with PollinationsService() as pollinations_service:
        retry_image_url, _ = await pollinations_service.generate_image(
            prompt=retry_prompt,
            brand_context=brand_context,
        )

    async with ImageValidationService() as validation_service:
        retry_validation = await validation_service.validate_image_url(retry_image_url)

    generation_time_ms = int((time.monotonic() - start_time) * 1000)

    if retry_validation.is_valid:
        logger.info("Retry validation passed")
        return CampaignImageResponse(
            image_url=retry_image_url,
            model="kontext",
            generation_time_ms=generation_time_ms,
            fallback_used=False,
            brand_applied=_is_brand_applied(brand_context),
            validation=_make_validation(
                retry_validation.width, retry_validation.height, retry_validation.is_valid
            ),
        )

    # Retry also failed - use fallback
    logger.warning("Retry validation failed, using fallback")
    async with PollinationsService() as fallback_service:
        fallback_url, _ = await fallback_service.generate_fallback(brand_context)

    return CampaignImageResponse(
        image_url=fallback_url,
        model="kontext",
        generation_time_ms=generation_time_ms,
        fallback_used=True,
        brand_applied=_is_brand_applied(brand_context),
        validation=_make_validation(0, 0, False),
    )
