"""Campaign Images API routes — real Cloudflare/Pollinations generation pipeline."""

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.models.brand_style import BrandStyleContextInternal, PollinationsPrompt
from src.models.campaign_image import (
    CampaignImageRequest,
    CampaignImageResponse,
    ValidationResult,
)
from src.models.errors import ErrorCode, create_error_response
from src.services.brand_style_service import BrandStyleService
from src.services.cloudflare_image_service import (
    CloudflareImageService,
    CloudflareImageServiceError,
)
from src.services.company_profile_service import CompanyProfileNotFoundError, CompanyProfileService
from src.services.image_validation_service import ImageValidationService
from src.services.pollinations_service import PollinationsService
from src.services.supabase import SupabaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaign-images", tags=["Campaign Images"])

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
async def generate_campaign_image(
    request: CampaignImageRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> CampaignImageResponse:
    """
    Generate a brand-styled campaign image.

    Primary provider is Cloudflare Workers AI: if the company profile has a
    reference image, it is used for image-to-image (Stable Diffusion img2img)
    so the output follows the reference's look; otherwise text-to-image (FLUX)
    is used. The generated image is uploaded to Supabase Storage and its public
    URL is returned. If Cloudflare fails, the route falls back to Pollinations.
    """
    start_time = time.monotonic()

    try:
        logger.info("Fetching company profile: %s", request.company_profile_id)
        profile = await company_profile_service.get_profile(str(request.company_profile_id))

        brand_context = brand_style_service.extract_brand_context(profile)

        prompt = brand_style_service.build_prompt(
            campaign_prompt=request.campaign_prompt,
            brand_context=brand_context,
            campaign_context=request.campaign_context,
        )

        reference_urls = brand_context.reference_image_urls or []
        try:
            image_url, model_name = await _generate_with_cloudflare(
                prompt=prompt,
                reference_urls=reference_urls,
                profile_id=str(request.company_profile_id),
            )
            fallback_used = False
        except CloudflareImageServiceError as e:
            logger.warning("Cloudflare generation failed, falling back to Pollinations: %s", e)
            image_url, model_name = await _generate_with_pollinations(prompt, brand_context)
            fallback_used = True

        logger.info("Validating generated image")
        async with ImageValidationService() as validation_service:
            validation_result = await validation_service.validate_image_url(image_url)

        generation_time_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "Campaign image generated in %dms (model=%s, fallback=%s)",
            generation_time_ms,
            model_name,
            fallback_used,
        )

        return CampaignImageResponse(
            image_url=image_url,
            model=model_name,
            generation_time_ms=generation_time_ms,
            fallback_used=fallback_used,
            brand_applied=_is_brand_applied(brand_context),
            validation=_make_validation(
                validation_result.width,
                validation_result.height,
                validation_result.is_valid,
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


async def _generate_with_cloudflare(
    prompt: PollinationsPrompt,
    reference_urls: list[str],
    profile_id: str,
) -> tuple[str, str]:
    """Generate via Cloudflare Workers AI and upload to Supabase.

    Uses img2img when a reference image is available (and downloadable),
    otherwise text2img. Returns (public_image_url, model_name).
    """
    async with CloudflareImageService() as cf:
        reference_bytes: bytes | None = None
        if reference_urls:
            logger.info("Downloading reference image: %s", reference_urls[0])
            reference_bytes = await cf.download_reference(reference_urls[0])

        if reference_bytes:
            logger.info("Generating with Cloudflare img2img (reference-guided)")
            image_bytes = await cf.generate_from_reference(
                prompt=prompt.base_prompt,
                reference_image_bytes=reference_bytes,
            )
            model_name = cf.img2img_model
        else:
            logger.info("No reference image; generating with Cloudflare text2img (flux)")
            image_bytes = await cf.generate_from_text(prompt=prompt.base_prompt)
            model_name = cf.text2img_model

    supabase = SupabaseService()
    filename = f"{profile_id}/{uuid.uuid4().hex}.png"
    public_url = supabase.upload_image_bytes(
        data=image_bytes,
        filename=filename,
        content_type="image/png",
        prefix="campaigns",
    )
    logger.info("Uploaded generated image to Supabase: %s", public_url)
    return public_url, model_name


async def _generate_with_pollinations(
    prompt: PollinationsPrompt,
    brand_context: BrandStyleContextInternal,
) -> tuple[str, str]:
    """Fallback generation via Pollinations. Returns (image_url, model_name)."""
    async with PollinationsService() as pollinations_service:
        model_name = pollinations_service.model
        try:
            image_url, _ = await pollinations_service.generate_image(
                prompt=prompt.base_prompt,
                brand_context=brand_context,
            )
        except Exception as e:
            logger.warning("Pollinations primary failed, using Pollinations fallback: %s", e)
            image_url, _ = await pollinations_service.generate_fallback(brand_context)
    return image_url, model_name
