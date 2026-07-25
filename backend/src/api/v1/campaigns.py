"""Campaign Management API routes — delegates to CampaignService/AssetService/HistoryService."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.models.campaign import CampaignState
from src.models.errors import NotFoundError
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
from src.services.campaign_service import CampaignService
from src.services.history_service import HistoryService

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
    """Create a new campaign in Draft state."""
    try:
        created = await svc.create_campaign(
            name=request.name,
            goals=request.goals.model_dump(mode="json"),
            target_audience=request.target_audience.model_dump(mode="json"),
            platforms=request.platforms,
            schedule=request.schedule.model_dump(mode="json"),
            metadata=request.metadata,
            company_profile_id=request.company_profile_id,
            organization_id=UUID(user.id),
            actor_id=UUID(user.id),
        )
    except ValueError as e:
        detail = str(e)
        if "already exists" in detail.lower():
            raise HTTPException(status_code=409, detail={"detail": detail, "code": "DUPLICATE_NAME"})
        raise HTTPException(status_code=422, detail=detail)
    return CampaignResponse.model_validate(created.to_dict())


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    state: Optional[CampaignState] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    owner_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: CampaignService = Depends(_get_campaign_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """List campaigns with filters and pagination."""
    campaigns, total = await svc.list_campaigns(
        organization_id=UUID(user.id),
        state=state,
        start_date=start_date,
        end_date=end_date,
        owner_id=owner_id,
        page=page,
        page_size=page_size,
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
    """Get campaign by ID."""
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
    reason: Optional[str] = None,
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
    """List all assets for a campaign."""
    campaign = await svc.get_campaign(campaign_id, UUID(user.id))
    if not campaign:
        raise NotFoundError("Campaign", str(campaign_id))

    assets = await asset_svc.list_assets(campaign_id)
    return AssetListResponse(
        assets=[AssetResponse.model_validate(a) for a in assets],
        total=len(assets),
    )
