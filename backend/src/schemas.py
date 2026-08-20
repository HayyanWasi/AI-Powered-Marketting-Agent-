"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.campaign import AssetSource, AssetType, CampaignState
from src.models.history import EventType

# ==================== Base Schemas ====================


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    code: str
    invalid_fields: list[str] | None = None


# ==================== Campaign Schemas ====================


class GoalsBase(BaseModel):
    """Campaign goals structure."""

    primary: str = Field(..., min_length=1)
    metrics: list[str] = Field(default_factory=list)
    targets: dict[str, Any] = Field(default_factory=dict)


class TargetAudienceBase(BaseModel):
    """Target audience definition."""

    segments: list[str] = Field(default_factory=list)
    demographics: dict[str, Any] = Field(default_factory=dict)
    interests: list[str] = Field(default_factory=list)


class ScheduleBase(BaseModel):
    """Campaign schedule."""

    start_date: datetime
    end_date: datetime
    timezone: str = Field(..., min_length=1)
    recurrence_rule: str | None = None


class CreateCampaignRequest(BaseModel):
    """Create campaign request."""

    name: str = Field(..., min_length=1, max_length=255)
    goals: GoalsBase
    target_audience: TargetAudienceBase
    platforms: list[str] = Field(..., min_items=1)
    schedule: ScheduleBase
    metadata: dict[str, Any] | None = None
    company_profile_id: UUID | None = None


class UpdateCampaignRequest(BaseModel):
    """Update campaign request (partial)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    goals: GoalsBase | None = None
    target_audience: TargetAudienceBase | None = None
    platforms: list[str] | None = None
    schedule: ScheduleBase | None = None
    metadata: dict[str, Any] | None = None
    company_profile_id: UUID | None = None


class CampaignResponse(BaseModel):
    """Campaign response with full details."""

    id: UUID
    organization_id: UUID
    company_profile_id: UUID | None = None
    name: str
    goals: dict[str, Any]
    target_audience: dict[str, Any]
    platforms: list[str]
    schedule: dict[str, Any]
    metadata: dict[str, Any]
    state: CampaignState
    version: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    archived_at: datetime | None = None
    created_by: UUID
    updated_by: UUID

    model_config = ConfigDict(from_attributes=True)


class CampaignSummary(BaseModel):
    """Campaign summary for list views."""

    id: UUID
    name: str
    state: CampaignState
    platforms: list[str]
    schedule: dict[str, Any]
    updated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignListParams(BaseModel):
    """Query parameters for listing campaigns."""

    state: CampaignState | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    owner_id: UUID | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class CampaignListResponse(BaseModel):
    """Paginated campaign list response."""

    campaigns: list[CampaignSummary]
    total: int
    page: int
    page_size: int


# ==================== State Transition Schemas ====================


class StateTransitionRequest(BaseModel):
    """State transition request."""

    to_state: CampaignState
    reason: str | None = Field(None, max_length=500)


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
    from_state: CampaignState | None = None
    to_state: CampaignState | None = None
    changed_fields: dict[str, Any] | None = None
    snapshot: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class HistoryListParams(BaseModel):
    """Query parameters for history listing."""

    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)


class HistoryListResponse(BaseModel):
    """Paginated history list response."""

    history: list[HistoryEntryResponse]
    total: int
    page: int
    page_size: int


# ==================== Asset Schemas ====================


class AssetContent(BaseModel):
    """Asset content - varies by type."""

    # For copy
    text: str | None = None
    format: str | None = None

    # For image
    url: str | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None

    # For hashtag set
    tags: list[str] | None = None

    # For metadata
    data: dict[str, Any] | None = None


class CreateAssetRequest(BaseModel):
    """Create asset request."""

    asset_type: AssetType
    content: dict[str, Any]
    source: AssetSource
    storage_path: str | None = None


class AssetResponse(BaseModel):
    """Asset response."""

    id: UUID
    campaign_id: UUID
    asset_type: AssetType
    content: dict[str, Any]
    storage_path: str | None = None
    source: AssetSource
    created_at: datetime
    created_by: UUID

    model_config = ConfigDict(from_attributes=True)


class AssetListResponse(BaseModel):
    """Asset list response."""

    assets: list[AssetResponse]
    total: int
