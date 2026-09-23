import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel

from src.agents.video_script_agent import VideoScene, VideoScriptAgent
from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.models.video_generation_context import VideoGenerationContext
from src.modules.planning.repositories.plan_repository import PlanNotFoundError
from src.modules.planning.services.plan_refinement_service import PlanRefinementService
from src.services.campaign_context_service import CampaignContextResolver, check_plan_freshness
from src.services.video_asset_service import VideoAssetPersistenceError, VideoAssetService
from src.services.video_generation_service import VideoGenerationError, VideoGenerationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["Video Generation"])

# Simple in-memory counter for per-campaign rate limiting (Task Requirement)
_campaign_generation_counts: dict[str, int] = {}
MAX_GENERATIONS_PER_CAMPAIGN = 100


class VideoGenerationRequest(BaseModel):
    prompt: str | None = None


class VideoGenerationResponse(BaseModel):
    video_url: str
    scenes: list[VideoScene]
    asset: dict
    draft_post: dict


@router.post(
    "/{campaign_id}/video",
    response_model=VideoGenerationResponse,
    summary="Generate interactive short-form video for a campaign",
)
async def generate_campaign_video(
    campaign_id: str = Path(..., description="The ID of the campaign"),
    request_data: VideoGenerationRequest | None = None,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> VideoGenerationResponse:
    """
    On-demand endpoint to generate a short-form video (TikTok/Reels/Shorts).
    1. Checks rate limit.
    2. Writes script using AI.
    3. Renders video with MoviePy and Edge-TTS.
    4. Uploads to Supabase.
    """
    try:
        campaign_uuid = UUID(campaign_id)
    except ValueError as exc:
        raise HTTPException(
            422, "A real campaign must be selected before generating video."
        ) from exc
    inputs = await CampaignContextResolver().resolve(campaign_uuid, user.id)
    campaign = inputs.campaign
    try:
        plan = await PlanRefinementService().get_plan(campaign_uuid)
    except PlanNotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail="Generate the campaign strategy before generating a campaign video.",
        ) from exc
    if plan.campaign_id != campaign_uuid:
        raise HTTPException(409, "The stored campaign strategy does not match this campaign.")
    is_stale, _ = check_plan_freshness(plan, inputs)
    if is_stale:
        raise HTTPException(
            status_code=409,
            detail="Campaign strategy is outdated because campaign or brand details changed. Regenerate the campaign strategy before generating a video.",
        )

    # 1. Rate Limiting Check
    current_count = _campaign_generation_counts.get(campaign_id, 0)
    if current_count >= MAX_GENERATIONS_PER_CAMPAIGN:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Campaign {campaign_id} has reached the maximum of {MAX_GENERATIONS_PER_CAMPAIGN} video generations.",
        )

    print(
        f"\n[VIDEO PIPELINE] >>> INCOMING GENERATION REQUEST for campaign '{campaign_id}'",
        flush=True,
    )
    if request_data and request_data.prompt:
        print(f"[VIDEO PIPELINE] Prompt: {request_data.prompt}", flush=True)

    logger.info("Starting on-demand video generation for campaign: %s", campaign_id)

    instruction = (
        request_data.prompt if request_data and request_data.prompt else "Create a campaign video."
    )
    video_context = VideoGenerationContext.from_sources(
        inputs=inputs,
        plan=plan,
        owner_id=UUID(user.id),
        user_instruction=instruction,
    )

    # Increment counter early to prevent concurrent spam
    _campaign_generation_counts[campaign_id] = current_count + 1

    try:
        # 3. Generate Script and Prompts
        print(
            "[VIDEO PIPELINE] Step 1: AI Director generating storytelling script & scene breakdown...",
            flush=True,
        )
        script_agent = VideoScriptAgent()
        scenes = await script_agent.generate_script(video_context)
        print(
            "\n[VIDEO PIPELINE] ==================== GENERATED STORY SCRIPT ====================",
            flush=True,
        )
        print(f"[VIDEO PIPELINE] Total Scenes: {len(scenes)}", flush=True)
        for i, sc in enumerate(scenes, 1):
            print(f'  [Scene {i}] Voiceover: "{sc.narration}"', flush=True)
            print(f'             Visual:    "{sc.image_prompt}"', flush=True)
        print(
            "[VIDEO PIPELINE] ================================================================\n",
            flush=True,
        )

        # 4. Generate Video File and Upload
        gen_service = VideoGenerationService()
        generated = await gen_service.generate_campaign_video(campaign_id, scenes, video_context)
        persisted = VideoAssetService().persist(
            campaign=campaign,
            user_id=UUID(user.id),
            media_url=generated.video_url,
            storage_path=generated.storage_path,
            prompt=instruction,
            scenes=[scene.model_dump(mode="json") for scene in scenes],
        )
        print(
            f"[VIDEO PIPELINE] Step 5: SUCCESS! Video attached to scheduler: {generated.video_url}\n",
            flush=True,
        )

        return VideoGenerationResponse(
            video_url=generated.video_url,
            scenes=scenes,
            asset=persisted["asset"],
            draft_post=persisted["post"],
        )

    except ValueError as ve:
        # Rollback counter on failure
        _campaign_generation_counts[campaign_id] = max(
            0, _campaign_generation_counts[campaign_id] - 1
        )
        logger.error("Script generation failed: %s", ve)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve)) from ve

    except VideoGenerationError as vge:
        _campaign_generation_counts[campaign_id] = max(
            0, _campaign_generation_counts[campaign_id] - 1
        )
        logger.error("Video rendering failed: %s", vge)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Rendering failed: {vge}"
        ) from vge

    except VideoAssetPersistenceError as exc:
        _campaign_generation_counts[campaign_id] = max(
            0, _campaign_generation_counts[campaign_id] - 1
        )
        logger.exception("Video scheduler attachment failed for campaign %s", campaign_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    except Exception as e:
        _campaign_generation_counts[campaign_id] = max(
            0, _campaign_generation_counts[campaign_id] - 1
        )
        logger.exception("Unexpected error during video generation for campaign %s", campaign_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Video generation failed. Please retry.",
        ) from e
