import logging
import uuid

import httpx
from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel

from src.models.image_generation import BrandSnapshot, ImageGenerationState
from src.services.campaign_service import CampaignService
from src.services.company_profile_service import CompanyProfileService
from src.services.image_iterative_service import ImageIterativeService
from src.services.pollinations_service import PollinationsService
from src.services.supabase import SupabaseService

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/campaigns/{campaign_id}/image-session", tags=["Iterative Image Generation"]
)


class StartSessionRequest(BaseModel):
    base_idea: str


class RefineSessionRequest(BaseModel):
    state: ImageGenerationState
    instruction: str


class FinalizeSessionRequest(BaseModel):
    state: ImageGenerationState
    image_url: str


class ImageSessionResponse(BaseModel):
    state: ImageGenerationState
    image_url: str


class FinalizeResponse(BaseModel):
    permanent_image_url: str
    caption: str


MAX_ITERATIONS = 25
_daily_generation_counts: dict[str, int] = {}
DAILY_CAP = 50


def _check_daily_cap(user_id: str):
    count = _daily_generation_counts.get(user_id, 0)
    if count >= DAILY_CAP:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily image generation cap reached ({DAILY_CAP}).",
        )
    _daily_generation_counts[user_id] = count + 1


@router.post("/start", response_model=ImageSessionResponse)
async def start_image_session(
    request: StartSessionRequest,
    campaign_id: str = Path(...),
):
    _check_daily_cap("global_user")

    try:
        from uuid import UUID as _UUID

        campaign_service = CampaignService()
        campaign = await campaign_service.get_campaign(_UUID(campaign_id))

        # Campaign is a Pydantic/dataclass object, access attributes directly
        company_profile_id = campaign.company_profile_id
        brand = BrandSnapshot()

        if company_profile_id:
            profile_service = CompanyProfileService()
            profile = await profile_service.get_profile(str(company_profile_id))
            # CompanyProfile fields: name, brand_colors, brand_personality, style_guide, industry_category
            brand.brand_name = profile.name or ""
            brand.industry = profile.industry_category or ""
            brand.tone_of_voice = profile.brand_personality or ""
            brand.personality_descriptors = []
            brand.color_palette = profile.brand_colors or []
            brand.style_guidance = profile.style_guide or ""

        iterative_service = ImageIterativeService()
        state = await iterative_service.initialize_state(request.base_idea, brand)

        pollinations = PollinationsService()
        image_url = pollinations._build_image_url(state.current_final_prompt)

        return ImageSessionResponse(state=state, image_url=image_url)
    except Exception as e:
        logger.error("Failed to start image session: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine", response_model=ImageSessionResponse)
async def refine_image_session(
    request: RefineSessionRequest,
    campaign_id: str = Path(...),
):
    if request.state.iteration_count >= MAX_ITERATIONS:
        raise HTTPException(status_code=400, detail="Maximum iterations reached for this session.")

    _check_daily_cap("global_user")

    try:
        iterative_service = ImageIterativeService()
        new_state = await iterative_service.refine_state(request.state, request.instruction)

        pollinations = PollinationsService()
        image_url = pollinations._build_image_url(new_state.current_final_prompt)

        return ImageSessionResponse(state=new_state, image_url=image_url)
    except Exception as e:
        logger.error("Failed to refine image session: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/finalize", response_model=FinalizeResponse)
async def finalize_image_session(
    request: FinalizeSessionRequest,
    campaign_id: str = Path(...),
):
    try:
        # Download image from Pollinations
        async with httpx.AsyncClient() as client:
            res = await client.get(request.image_url)
            res.raise_for_status()
            image_bytes = res.content

        supabase = SupabaseService()
        filename = f"{campaign_id}/{uuid.uuid4()}.jpg"
        # Supabase service might not have a direct bytes upload wrapper matching exactly, let's just use raw client
        res = supabase.client.storage.from_("brand_images").upload(
            path=filename, file=image_bytes, file_options={"content-type": "image/jpeg"}
        )
        permanent_url = supabase.client.storage.from_("brand_images").get_public_url(filename)

        iterative_service = ImageIterativeService()
        caption = await iterative_service.generate_caption(
            base_idea=request.state.base_idea,
            tone=request.state.brand_snapshot.tone_of_voice,
        )

        return FinalizeResponse(permanent_image_url=permanent_url, caption=caption)
    except Exception as e:
        logger.error("Failed to finalize image session: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
