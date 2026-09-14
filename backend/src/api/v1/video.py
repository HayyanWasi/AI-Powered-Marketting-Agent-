import logging

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel

from src.agents.video_script_agent import VideoScene, VideoScriptAgent
from src.services.campaign_service import CampaignService
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


@router.post(
    "/{campaign_id}/video",
    response_model=VideoGenerationResponse,
    summary="Generate interactive short-form video for a campaign",
)
async def generate_campaign_video(
    campaign_id: str = Path(..., description="The ID of the campaign"),
    request_data: VideoGenerationRequest | None = None,
) -> VideoGenerationResponse:
    """
    On-demand endpoint to generate a short-form video (TikTok/Reels/Shorts).
    1. Checks rate limit.
    2. Writes script using AI.
    3. Renders video with MoviePy and Edge-TTS.
    4. Uploads to Supabase.
    """
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

    # 2. Get Campaign Context
    if request_data and request_data.prompt:
        context_str = request_data.prompt
    else:
        try:
            service = CampaignService()
            campaign = await service.get_campaign(campaign_id)
            context_str = f"Campaign Name: {campaign.get('name', 'Unknown')}\nGoal: {campaign.get('goal', 'Unknown')}"
        except Exception as e:
            logger.warning("Could not fetch full campaign context, using fallback context: %s", e)
            context_str = "High-energy promotional video for our latest marketing event."

    # Increment counter early to prevent concurrent spam
    _campaign_generation_counts[campaign_id] = current_count + 1

    try:
        # 3. Generate Script and Prompts
        print(
            "[VIDEO PIPELINE] Step 1: AI Director generating storytelling script & scene breakdown...",
            flush=True,
        )
        script_agent = VideoScriptAgent()
        scenes = await script_agent.generate_script(context_str)
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
        video_url = await gen_service.generate_campaign_video(campaign_id, scenes)
        print(f"[VIDEO PIPELINE] Step 4: SUCCESS! Video URL: {video_url}\n", flush=True)

        return VideoGenerationResponse(video_url=video_url, scenes=scenes)

    except ValueError as ve:
        # Rollback counter on failure
        _campaign_generation_counts[campaign_id] = max(
            0, _campaign_generation_counts[campaign_id] - 1
        )
        logger.error("Script generation failed: %s", ve)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    except VideoGenerationError as vge:
        _campaign_generation_counts[campaign_id] = max(
            0, _campaign_generation_counts[campaign_id] - 1
        )
        logger.error("Video rendering failed: %s", vge)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Rendering failed: {vge}"
        )

    except Exception as e:
        _campaign_generation_counts[campaign_id] = max(
            0, _campaign_generation_counts[campaign_id] - 1
        )
        import traceback

        tb = traceback.format_exc()
        logger.error("Unexpected error during video generation: %s\n%s", e, tb)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {e}\n{tb}"
        )
