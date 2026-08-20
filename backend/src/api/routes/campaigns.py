"""Campaign API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from src.models.campaign import CampaignState
from src.models.errors import (
    DuplicateNameError,
    NotFoundError,
    PreconditionFailedError,
    StateTransitionError,
    ValidationError,
    VersionConflictError,
)
from src.schemas import (
    AssetListResponse,
    AssetResponse,
    CampaignListResponse,
    CampaignResponse,
    CampaignSummary,
    CreateAssetRequest,
    CreateCampaignRequest,
    ErrorResponse,
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

# Services - lazy initialized to avoid import-time env var requirements
_campaign_service: CampaignService | None = None
_asset_service: AssetService | None = None
_history_service: HistoryService | None = None


def _get_campaign_service() -> CampaignService:
    global _campaign_service
    if _campaign_service is None:
        _campaign_service = CampaignService()
    return _campaign_service


def _get_asset_service() -> AssetService:
    global _asset_service
    if _asset_service is None:
        _asset_service = AssetService()
    return _asset_service


def _get_history_service() -> HistoryService:
    global _history_service
    if _history_service is None:
        _history_service = HistoryService()
    return _history_service


# ==================== Helper ====================


def get_organization_id() -> UUID:
    """Extract organization ID from auth context (placeholder)."""
    # In real implementation, get from JWT token
    return UUID("00000000-0000-0000-0000-000000000001")


def get_actor_id() -> UUID:
    """Extract actor/user ID from auth context (placeholder)."""
    return UUID("00000000-0000-0000-0000-000000000002")


# ==================== Campaign CRUD ====================


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def create_campaign(request: CreateCampaignRequest):
    """Create a new campaign in Draft state."""
    try:
        org_id = get_organization_id()
        actor_id = get_actor_id()

        created = await _get_campaign_service().create_campaign(
            name=request.name,
            goals=request.goals.model_dump(mode="json"),
            target_audience=request.target_audience.model_dump(mode="json"),
            platforms=request.platforms,
            schedule=request.schedule.model_dump(mode="json"),
            metadata=request.metadata,
            company_profile_id=request.company_profile_id,
            organization_id=org_id,
            actor_id=actor_id,
        )
        return CampaignResponse(**created.to_dict())

    except DuplicateNameError as e:
        raise HTTPException(status_code=409, detail={"detail": str(e), "code": "DUPLICATE_NAME"})
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": str(e),
                "code": "VALIDATION_ERROR",
                "invalid_fields": e.invalid_fields,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"detail": f"Failed to create campaign: {e}", "code": "INTERNAL_ERROR"},
        )


@router.get(
    "",
    response_model=CampaignListResponse,
    responses={400: {"model": ErrorResponse}},
)
async def list_campaigns(
    state: CampaignState | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    owner_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List campaigns with filters and pagination."""
    org_id = get_organization_id()

    campaigns, total = await _get_campaign_service().list_campaigns(
        organization_id=org_id,
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


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_campaign(campaign_id: UUID):
    """Get campaign by ID with assets."""
    org_id = get_organization_id()
    campaign = await _get_campaign_service().get_campaign(campaign_id, org_id)

    if not campaign:
        raise NotFoundError("Campaign", str(campaign_id))

    return CampaignResponse.model_validate(campaign.to_dict())


@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        412: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def update_campaign(
    campaign_id: UUID,
    request: UpdateCampaignRequest,
    if_match: str = Header(..., alias="If-Match"),
):
    """Update campaign configuration (Draft only) with optimistic locking."""
    try:
        expected_version = int(if_match)
        org_id = get_organization_id()
        actor_id = get_actor_id()

        updated = await _get_campaign_service().update_campaign(
            campaign_id=campaign_id,
            organization_id=org_id,
            actor_id=actor_id,
            updates=request.model_dump(exclude_unset=True),
            expected_version=expected_version,
        )

        return CampaignResponse.model_validate(updated.to_dict())

    except ValueError:
        raise HTTPException(
            status_code=412,
            detail={"detail": "Invalid If-Match header", "code": "PRECONDITION_FAILED"},
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={"detail": str(e), "code": "NOT_FOUND"})
    except VersionConflictError as e:
        raise HTTPException(status_code=409, detail={"detail": str(e), "code": "VERSION_CONFLICT"})
    except StateTransitionError as e:
        raise HTTPException(
            status_code=409, detail={"detail": str(e), "code": "STATE_TRANSITION_INVALID"}
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": str(e),
                "code": "VALIDATION_ERROR",
                "invalid_fields": e.invalid_fields,
            },
        )


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def delete_campaign(campaign_id: UUID):
    """Delete a campaign (Draft only)."""
    try:
        org_id = get_organization_id()
        actor_id = get_actor_id()
        await _get_campaign_service().delete_campaign(campaign_id, org_id, actor_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={"detail": str(e), "code": "NOT_FOUND"})
    except StateTransitionError as e:
        raise HTTPException(
            status_code=409, detail={"detail": str(e), "code": "STATE_TRANSITION_INVALID"}
        )


# ==================== State Transitions ====================


@router.post(
    "/{campaign_id}/transition",
    response_model=StateTransitionResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def transition_campaign(campaign_id: UUID, request: StateTransitionRequest):
    """Transition campaign to a new state."""
    try:
        org_id = get_organization_id()
        actor_id = get_actor_id()

        campaign = await _get_campaign_service().transition_campaign(
            campaign_id=campaign_id,
            organization_id=org_id,
            actor_id=actor_id,
            to_state=request.to_state,
            reason=request.reason,
        )

        # Get the history entry that was just created
        history = await _get_history_service().get_history(campaign_id, page=1, page_size=1)
        history_entry = history[0] if history else None

        return StateTransitionResponse(
            campaign=CampaignResponse.model_validate(campaign.to_dict()),
            history_entry=(
                HistoryEntryResponse.model_validate(history_entry.to_dict())
                if history_entry
                else None
            ),
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={"detail": str(e), "code": "NOT_FOUND"})
    except StateTransitionError as e:
        raise HTTPException(
            status_code=409, detail={"detail": str(e), "code": "STATE_TRANSITION_INVALID"}
        )
    except PreconditionFailedError as e:
        raise HTTPException(
            status_code=409, detail={"detail": str(e), "code": "PRECONDITION_FAILED"}
        )


@router.post(
    "/{campaign_id}/archive",
    response_model=CampaignResponse,
    responses={404: {"model": ErrorResponse}},
)
async def archive_campaign(campaign_id: UUID, reason: str | None = None):
    """Archive a campaign from any state."""
    try:
        org_id = get_organization_id()
        actor_id = get_actor_id()

        campaign = await _get_campaign_service().archive_campaign(
            campaign_id=campaign_id,
            organization_id=org_id,
            actor_id=actor_id,
            reason=reason,
        )

        return CampaignResponse.model_validate(campaign.to_dict())

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={"detail": str(e), "code": "NOT_FOUND"})


@router.post(
    "/{campaign_id}/restore",
    response_model=CampaignResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def restore_campaign(campaign_id: UUID):
    """Restore an archived campaign to its previous state."""
    try:
        org_id = get_organization_id()
        actor_id = get_actor_id()

        campaign = await _get_campaign_service().restore_campaign(
            campaign_id=campaign_id,
            organization_id=org_id,
            actor_id=actor_id,
        )

        return CampaignResponse.model_validate(campaign.to_dict())

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={"detail": str(e), "code": "NOT_FOUND"})
    except StateTransitionError as e:
        raise HTTPException(
            status_code=409, detail={"detail": str(e), "code": "STATE_TRANSITION_INVALID"}
        )


# ==================== History ====================


@router.get(
    "/{campaign_id}/history",
    response_model=HistoryListResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_campaign_history(
    campaign_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Get campaign history with pagination."""
    org_id = get_organization_id()

    # Verify campaign exists and belongs to org
    campaign = await _get_campaign_service().get_campaign(campaign_id, org_id)
    if not campaign:
        raise NotFoundError("Campaign", str(campaign_id))

    entries, total = await _get_history_service().get_history(campaign_id, page, page_size)

    return HistoryListResponse(
        history=[HistoryEntryResponse.model_validate(e.to_dict()) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


# ==================== Assets ====================


@router.post(
    "/{campaign_id}/assets",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def create_asset(campaign_id: UUID, request: CreateAssetRequest):
    """Associate an asset with a campaign."""
    try:
        org_id = get_organization_id()
        actor_id = get_actor_id()

        # Verify campaign exists
        campaign = await _get_campaign_service().get_campaign(campaign_id, org_id)
        if not campaign:
            raise NotFoundError("Campaign", str(campaign_id))

        asset = await _get_asset_service().create_asset(
            campaign_id=campaign_id,
            asset_type=request.asset_type,
            content=request.content,
            source=request.source,
            actor_id=actor_id,
            storage_path=request.storage_path,
        )

        return AssetResponse.model_validate(asset.to_dict())

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={"detail": str(e), "code": "NOT_FOUND"})
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": str(e),
                "code": "VALIDATION_ERROR",
                "invalid_fields": e.invalid_fields,
            },
        )


@router.get(
    "/{campaign_id}/assets",
    response_model=AssetListResponse,
    responses={404: {"model": ErrorResponse}},
)
async def list_assets(campaign_id: UUID):
    """List all assets for a campaign."""
    org_id = get_organization_id()

    campaign = await _get_campaign_service().get_campaign(campaign_id, org_id)
    if not campaign:
        raise NotFoundError("Campaign", str(campaign_id))

    assets = await _get_asset_service().list_assets(campaign_id)

    return AssetListResponse(
        assets=[AssetResponse.model_validate(a) for a in assets],
        total=len(assets),
    )
