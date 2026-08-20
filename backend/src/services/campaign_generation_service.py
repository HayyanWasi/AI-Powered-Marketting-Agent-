"""Campaign generation — single real entry point used by every workflow route.

Builds a GenerationContext via ContextBuilder and runs it through the
LangGraph-backed Orchestrator (src/agents/orchestrator.py). No route may
substitute hardcoded/placeholder content for a failed pipeline run; a failed
AgentResult always surfaces as an exception here.
"""

import logging
from datetime import datetime
from uuid import UUID

from src.agents.context_builder import ContextBuilder
from src.agents.orchestrator import Orchestrator
from src.models.campaign import AssetSource, AssetType, CampaignAsset
from src.repositories.campaign_repository import AssetRepository
from src.services.campaign_service import CampaignService

logger = logging.getLogger(__name__)

_DEFAULT_PLATFORMS = ["instagram", "linkedin", "facebook"]

# Placeholder identity until auth/org context is threaded through this route.
_ORG_ID = UUID("00000000-0000-0000-0000-000000000001")
_ACTOR_ID = UUID("00000000-0000-0000-0000-000000000002")


class CampaignGenerationError(Exception):
    """Raised when the generation pipeline fails."""


async def run_campaign_generation(initial_state: dict) -> dict:
    """Run the real campaign-generation pipeline and persist its output.

    Args:
        initial_state: Caller-supplied inputs. Recognized keys: prompt,
            company_profile_id, guest_names, event_name, event_date, venue,
            platforms, registration_link.

    Returns:
        {"campaign_id": str, "image_url": str | None, "status": "completed"}

    Raises:
        CampaignGenerationError: If the pipeline reports failure.
    """
    prompt = initial_state.get("prompt", "Marketing campaign")
    company_profile_id = initial_state.get("company_profile_id")
    platforms = initial_state.get("platforms") or _DEFAULT_PLATFORMS
    user_goal = initial_state.get("user_goal") or prompt
    campaign_id_raw = initial_state.get("campaign_id")
    campaign_id: UUID | None = UUID(str(campaign_id_raw)) if campaign_id_raw else None

    context = ContextBuilder().build(
        company_profile_id=str(company_profile_id) if company_profile_id else None,
        guest_names=initial_state.get("guest_names"),
        event_name=initial_state.get("event_name") or user_goal,
        event_date=initial_state.get("event_date", ""),
        venue=initial_state.get("venue", ""),
        platforms=platforms,
        registration_link=initial_state.get("registration_link", ""),
        user_goal=user_goal,
        campaign_id=campaign_id,
    )

    result = await Orchestrator().execute(context)

    if not result.success:
        raise CampaignGenerationError(result.message)

    final_context = result.context

    campaign_service = CampaignService()
    campaign = await campaign_service.create_campaign(
        name=user_goal[:100],
        goals={
            "primary": user_goal,
            "metrics": ["engagement", "reach", "registrations"],
        },
        target_audience={
            "segments": [
                p.name for p in (final_context.plan.core_strategy.personas if final_context.plan else [])
            ] or ["general"],
            "demographics": {},
            "interests": [],
        },
        platforms=list(platforms),
        schedule={
            "start_date": datetime.now().isoformat(),
            "end_date": datetime.now().isoformat(),
            "timezone": "UTC",
        },
        company_profile_id=UUID(str(company_profile_id)) if company_profile_id else None,
        organization_id=_ORG_ID,
        actor_id=_ACTOR_ID,
    )

    cta = final_context.strategy.cta_hierarchy[-1] if final_context.strategy.cta_hierarchy else ""

    asset_repo = AssetRepository()
    image_url = None
    for draft in final_context.content_drafts:
        copy_asset = CampaignAsset(
            campaign_id=campaign.id,
            asset_type=AssetType.COPY,
            content={
                "text": draft.selected_variant or draft.variant_a,
                "headlines": [draft.variant_a, draft.variant_b, draft.variant_c],
                "cta": cta,
                "hashtags": list(final_context.hashtags),
            },
            source=AssetSource.AI,
            created_by=_ACTOR_ID,
        )
        await asset_repo.create(copy_asset)

        if draft.image_url:
            image_url = draft.image_url
            image_asset = CampaignAsset(
                campaign_id=campaign.id,
                asset_type=AssetType.IMAGE,
                content={"url": draft.image_url, "prompt": draft.image_prompt},
                storage_path=draft.image_url,
                source=AssetSource.AI,
                created_by=_ACTOR_ID,
            )
            await asset_repo.create(image_asset)

    logger.info(
        "Campaign %s generated with %d content drafts",
        campaign.id,
        len(final_context.content_drafts),
    )

    return {
        "campaign_id": str(campaign.id),
        "image_url": image_url,
        "status": "completed",
    }
