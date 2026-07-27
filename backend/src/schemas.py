"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from src.models.campaign import CampaignState
from src.models.history import EventType
from src.models.campaign import AssetType, AssetSource

# ==================== Base Schemas ====================


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    code: str
    invalid_fields: Optional[List[str]] = None


# ==================== Campaign Schemas ====================


class GoalsBase(BaseModel):
    """Campaign goals structure."""

    primary: str = Field(..., min_length=1)
    metrics: List[str] = Field(default_factory=list)
    targets: Dict[str, Any] = Field(default_factory=dict)


class TargetAudienceBase(BaseModel):
    """Target audience definition."""

    segments: List[str] = Field(default_factory=list)
    demographics: Dict[str, Any] = Field(default_factory=dict)
    interests: List[str] = Field(default_factory=list)


class ScheduleBase(BaseModel):
    """Campaign schedule."""

    start_date: datetime
    end_date: datetime
    timezone: str = Field(..., min_length=1)
    recurrence_rule: Optional[str] = None


class CreateCampaignRequest(BaseModel):
    """Create campaign request."""

    name: str = Field(..., min_length=1, max_length=255)
    goals: GoalsBase
    target_audience: TargetAudienceBase
    platforms: List[str] = Field(..., min_items=1)
    schedule: ScheduleBase
    metadata: Optional[Dict[str, Any]] = None
    company_profile_id: Optional[UUID] = None


class UpdateCampaignRequest(BaseModel):
    """Update campaign request (partial)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    goals: Optional[GoalsBase] = None
    target_audience: Optional[TargetAudienceBase] = None
    platforms: Optional[List[str]] = None
    schedule: Optional[ScheduleBase] = None
    metadata: Optional[Dict[str, Any]] = None
    company_profile_id: Optional[UUID] = None


class CampaignResponse(BaseModel):
    """Campaign response with full details."""

    id: UUID
    organization_id: UUID
    company_profile_id: Optional[UUID] = None
    name: str
    goals: Dict[str, Any]
    target_audience: Dict[str, Any]
    platforms: List[str]
    schedule: Dict[str, Any]
    metadata: Dict[str, Any]
    state: CampaignState
    version: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_by: UUID
    updated_by: UUID

    model_config = ConfigDict(from_attributes=True)


class CampaignSummary(BaseModel):
    """Campaign summary for list views."""

    id: UUID
    name: str
    state: CampaignState
    platforms: List[str]
    schedule: Dict[str, Any]
    updated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignListParams(BaseModel):
    """Query parameters for listing campaigns."""

    state: Optional[CampaignState] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    owner_id: Optional[UUID] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class CampaignListResponse(BaseModel):
    """Paginated campaign list response."""

    campaigns: List[CampaignSummary]
    total: int
    page: int
    page_size: int


# ==================== State Transition Schemas ====================


class StateTransitionRequest(BaseModel):
    """State transition request."""

    to_state: CampaignState
    reason: Optional[str] = Field(None, max_length=500)


class StateTransitionResponse(BaseModel):
    """State transition response with history entry."""

    campaign: CampaignResponse
    history_entry: Optional["HistoryEntryResponse"] = None


# ==================== History Schemas ====================


class HistoryEntryResponse(BaseModel):
    """History entry response."""

    id: UUID
    campaign_id: UUID
    event_type: EventType
    timestamp: datetime
    actor_id: UUID
    from_state: Optional[CampaignState] = None
    to_state: Optional[CampaignState] = None
    changed_fields: Optional[Dict[str, Any]] = None
    snapshot: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class HistoryListParams(BaseModel):
    """Query parameters for history listing."""

    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)


class HistoryListResponse(BaseModel):
    """Paginated history list response."""

    history: List[HistoryEntryResponse]
    total: int
    page: int
    page_size: int


# ==================== Asset Schemas ====================


class AssetContent(BaseModel):
    """Asset content - varies by type."""

    # For copy
    text: Optional[str] = None
    format: Optional[str] = None

    # For image
    url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    mime_type: Optional[str] = None

    # For hashtag set
    tags: Optional[List[str]] = None

    # For metadata
    data: Optional[Dict[str, Any]] = None


class CreateAssetRequest(BaseModel):
    """Create asset request."""

    asset_type: AssetType
    content: Dict[str, Any]
    source: AssetSource
    storage_path: Optional[str] = None


class AssetResponse(BaseModel):
    """Asset response."""

    id: UUID
    campaign_id: UUID
    asset_type: AssetType
    content: Dict[str, Any]
    storage_path: Optional[str] = None
    source: AssetSource
    created_at: datetime
    created_by: UUID

    model_config = ConfigDict(from_attributes=True)


class AssetListResponse(BaseModel):
    """Asset list response."""

    assets: List[AssetResponse]
    total: int
