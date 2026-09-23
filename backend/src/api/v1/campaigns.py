"""Campaign Management API routes — delegates to CampaignService/AssetService/HistoryService."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.models.campaign import CampaignState
from src.models.errors import NotFoundError
from src.repositories.base import BaseRepository
from src.schemas import (
    AssetListResponse,
    AssetResponse,
    CampaignListResponse,
    CampaignResponse,
    CampaignSummary,
    CreateAssetRequest,
    CreateCampaignRequest,
    HistoryEntryResponse,
    HistoryListResponse,
    StateTransitionRequest,
    StateTransitionResponse,
    UpdateCampaignRequest,
)
from src.services.asset_service import AssetService
from src.services.campaign_context_service import require_profile
from src.services.campaign_service import CampaignService
from src.services.history_service import HistoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


async def _get_campaign_service() -> CampaignService:
    return CampaignService()


async def _get_asset_service() -> AssetService:
    return AssetService()


async def _get_history_service() -> HistoryService:
    return HistoryService()


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    request: CreateCampaignRequest,
    svc: CampaignService = Depends(_get_campaign_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Create a new campaign."""
    require_profile(request.company_profile_id, user.id)
    campaign = await svc.create_campaign(
        organization_id=UUID(user.id),
        name=request.name,
        goals=request.goals.model_dump(),
        target_audience=request.target_audience.model_dump(),
        platforms=request.platforms,
        schedule=request.schedule.model_dump(),
        actor_id=UUID(user.id),
        company_profile_id=request.company_profile_id,
        metadata=request.metadata,
    )
    return CampaignResponse.model_validate(campaign.to_dict())


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    company_profile_id: UUID | None = Query(None),
    state: CampaignState | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    owner_id: UUID | None = Query(None),
    svc: CampaignService = Depends(_get_campaign_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """List campaigns with optional filtering and pagination."""
    campaigns, total = await svc.list_campaigns(
        organization_id=UUID(user.id),
        state=state,
        owner_id=owner_id,
        page=page,
        page_size=page_size,
        company_profile_id=company_profile_id,
    )
    return CampaignListResponse(
        campaigns=[CampaignSummary.model_validate(c.to_dict()) for c in campaigns],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    svc: CampaignService = Depends(_get_campaign_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Get the authenticated user's campaign."""
    campaign = await svc.get_campaign(campaign_id, UUID(user.id))

    if not campaign:
        raise NotFoundError("Campaign", str(campaign_id))
    return CampaignResponse.model_validate(campaign.to_dict())


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    request: UpdateCampaignRequest,
    if_match: str = Header(..., alias="If-Match"),
    svc: CampaignService = Depends(_get_campaign_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Update campaign configuration (Draft only) with optimistic locking."""
    await svc.get_campaign(campaign_id, UUID(user.id))
    if "company_profile_id" in request.model_fields_set:
        if request.company_profile_id is None:
            raise HTTPException(422, "A company profile is required.")
        require_profile(request.company_profile_id, user.id)
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(
            status_code=412,
            detail={"detail": "Invalid If-Match header", "code": "PRECONDITION_FAILED"},
        )

    updated = await svc.update_campaign(
        campaign_id=campaign_id,
        actor_id=UUID(user.id),
        updates=request.model_dump(exclude_unset=True),
        expected_version=expected_version,
    )
    return CampaignResponse.model_validate(updated.to_dict())


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: UUID,
    svc: CampaignService = Depends(_get_campaign_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Delete a campaign (Draft only)."""
    await svc.delete_campaign(campaign_id, UUID(user.id))


@router.post("/{campaign_id}/transition", response_model=StateTransitionResponse)
async def transition_campaign(
    campaign_id: UUID,
    request: StateTransitionRequest,
    svc: CampaignService = Depends(_get_campaign_service),
    history_svc: HistoryService = Depends(_get_history_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Transition campaign to a new state."""
    campaign = await svc.transition_campaign(
        campaign_id=campaign_id,
        actor_id=UUID(user.id),
        to_state=request.to_state,
        reason=request.reason,
    )
    history_entries, _ = await history_svc.get_history(campaign_id, page=1, page_size=1)
    history_entry = history_entries[0] if history_entries else None
    return StateTransitionResponse(
        campaign=CampaignResponse.model_validate(campaign.to_dict()),
        history_entry=(
            HistoryEntryResponse.model_validate(history_entry.to_dict()) if history_entry else None
        ),
    )


@router.post("/{campaign_id}/archive", response_model=CampaignResponse)
async def archive_campaign(
    campaign_id: UUID,
    reason: str | None = None,
    svc: CampaignService = Depends(_get_campaign_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Archive a campaign from any state."""
    campaign = await svc.archive_campaign(
        campaign_id=campaign_id,
        actor_id=UUID(user.id),
        reason=reason,
    )
    return CampaignResponse.model_validate(campaign.to_dict())


@router.post("/{campaign_id}/restore", response_model=CampaignResponse)
async def restore_campaign(
    campaign_id: UUID,
    svc: CampaignService = Depends(_get_campaign_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Restore an archived campaign to its previous state."""
    campaign = await svc.restore_campaign(campaign_id=campaign_id, actor_id=UUID(user.id))
    return CampaignResponse.model_validate(campaign.to_dict())


@router.get("/{campaign_id}/history", response_model=HistoryListResponse)
async def get_campaign_history(
    campaign_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    svc: CampaignService = Depends(_get_campaign_service),
    history_svc: HistoryService = Depends(_get_history_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Get campaign history with pagination."""
    campaign = await svc.get_campaign(campaign_id, UUID(user.id))
    if not campaign:
        raise NotFoundError("Campaign", str(campaign_id))

    entries, total = await history_svc.get_history(campaign_id, page, page_size)
    return HistoryListResponse(
        history=[HistoryEntryResponse.model_validate(e.to_dict()) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{campaign_id}/assets",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_asset(
    campaign_id: UUID,
    request: CreateAssetRequest,
    svc: CampaignService = Depends(_get_campaign_service),
    asset_svc: AssetService = Depends(_get_asset_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Associate an asset with a campaign."""
    campaign = await svc.get_campaign(campaign_id, UUID(user.id))
    if not campaign:
        raise NotFoundError("Campaign", str(campaign_id))

    asset = await asset_svc.create_asset(
        campaign_id=campaign_id,
        asset_type=request.asset_type,
        content=request.content,
        source=request.source,
        actor_id=UUID(user.id),
        storage_path=request.storage_path,
    )
    return AssetResponse.model_validate(asset.to_dict())


@router.get("/{campaign_id}/assets", response_model=AssetListResponse)
async def list_assets(
    campaign_id: UUID,
    svc: CampaignService = Depends(_get_campaign_service),
    asset_svc: AssetService = Depends(_get_asset_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """List all assets for a campaign with dev fallback."""
    try:
        campaign = await svc.get_campaign(campaign_id, UUID(user.id))
    except NotFoundError:
        campaign = await svc.campaign_repository.get_by_id(campaign_id, None)
    campaign = await svc.get_campaign(campaign_id, UUID(user.id))

    if not campaign:
        raise NotFoundError("Campaign", str(campaign_id))

    assets = await asset_svc.list_assets(campaign_id)
    return AssetListResponse(
        assets=[AssetResponse.model_validate(a) for a in assets],
        total=len(assets),
    )


@router.get("/{campaign_id}/posts")
async def get_campaign_posts(
    campaign_id: UUID,
    svc: CampaignService = Depends(_get_campaign_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[dict[str, Any]]:
    """Get all generated/scheduled posts for this campaign."""
    campaign = await svc.get_campaign(campaign_id, UUID(user.id))
    if not campaign:
        raise NotFoundError("Campaign", str(campaign_id))

    posts_repo = BaseRepository("linkedin_posts")
    try:
        res = (
            posts_repo.client.table("linkedin_posts")
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .order("created_at", desc=False)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.warning("Could not fetch posts for campaign %s: %s", campaign_id, e)
        return []
