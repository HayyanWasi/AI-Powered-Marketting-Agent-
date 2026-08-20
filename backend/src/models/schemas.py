"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.campaign import CampaignState
from src.models.history import EventType


class AssetType(str, Enum):
    """Asset type categories."""

    COPY = "copy"
    IMAGE = "image"
    HASHTAG_SET = "hashtag_set"
    METADATA = "metadata"
    OTHER = "other"


class AssetSource(str, Enum):
    """Origin of the asset."""

    AI = "ai"
    MANUAL = "manual"
    IMPORTED = "imported"


class Platform(str, Enum):
    """Supported social platforms."""

    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    PINTEREST = "pinterest"


# ==================== Error Responses ====================


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


class CampaignBase(BaseModel):
    """Base campaign fields."""

    name: str = Field(..., min_length=1, max_length=255)
    goals: GoalsBase
    target_audience: TargetAudienceBase
    platforms: list[str] = Field(..., min_length=1)
    schedule: ScheduleBase
    metadata: dict[str, Any] | None = None
    company_profile_id: UUID | None = None


class CreateCampaignRequest(CampaignBase):
    """Request to create a new campaign."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Q4 Holiday Sale 2026",
                "goals": {
                    "primary": "Drive holiday sales",
                    "metrics": ["revenue", "conversion_rate"],
                    "targets": {"revenue": 50000, "conversion_rate": 0.03},
                },
                "target_audience": {
                    "segments": ["existing_customers", "high_value"],
                    "demographics": {"age_range": "25-45", "location": "US"},
                    "interests": ["holiday shopping", "deals"],
                },
                "platforms": ["instagram", "facebook", "linkedin"],
                "schedule": {
                    "start_date": "2026-11-15T09:00:00Z",
                    "end_date": "2026-12-31T23:59:59Z",
                    "timezone": "America/New_York",
                },
                "metadata": {"campaign_type": "seasonal", "budget": 10000},
            }
        }
    )


class UpdateCampaignRequest(BaseModel):
    """Request to update campaign configuration (Draft only)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    goals: GoalsBase | None = None
    target_audience: TargetAudienceBase | None = None
    platforms: list[str] | None = None
    schedule: ScheduleBase | None = None
    metadata: dict[str, Any] | None = None
    company_profile_id: UUID | None = None


class CampaignResponse(BaseModel):
    """Full campaign response."""

    id: UUID
    organization_id: UUID
    company_profile_id: UUID | None
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


class CampaignListResponse(BaseModel):
    """Paginated campaign list response."""

    campaigns: list[CampaignSummary]
    total: int
    page: int
    page_size: int


# ==================== State Transition ====================


class StateTransitionRequest(BaseModel):
    """Request to transition campaign state."""

    to_state: CampaignState
    reason: str | None = Field(None, max_length=500)


class StateTransitionResponse(BaseModel):
    """Response after state transition."""

    campaign: CampaignResponse
    history_entry: "HistoryEntryResponse"


# ==================== History ====================


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


class HistoryListResponse(BaseModel):
    """Paginated history response."""

    history: list[HistoryEntryResponse]
    total: int
    page: int
    page_size: int


# ==================== Assets ====================


class CopyContent(BaseModel):
    """Copy asset content."""

    asset_type: str = "copy"
    text: str
    format: str = "markdown"


class ImageContent(BaseModel):
    """Image asset content."""

    asset_type: str = "image"
    url: str
    width: int
    height: int
    mime_type: str


class HashtagSetContent(BaseModel):
    """Hashtag set asset content."""

    asset_type: str = "hashtag_set"
    tags: list[str]


class MetadataContent(BaseModel):
    """Metadata asset content."""

    asset_type: str = "metadata"
    data: dict[str, Any]


AssetContent = CopyContent | ImageContent | HashtagSetContent | MetadataContent


class CreateAssetRequest(BaseModel):
    """Request to associate an asset with a campaign."""

    asset_type: str = Field(..., pattern="^(copy|image|hashtag_set|metadata|other)$")
    content: AssetContent
    source: str = Field(..., pattern="^(ai|manual|imported)$")
    storage_path: str | None = None


class AssetResponse(BaseModel):
    """Asset response."""

    id: UUID
    campaign_id: UUID
    asset_type: str
    content: AssetContent
    storage_path: str | None = None
    source: str
    created_at: datetime
    created_by: UUID

    model_config = ConfigDict(from_attributes=True)


class AssetListResponse(BaseModel):
    """Asset list response."""

    assets: list[AssetResponse]
    total: int


# ==================== Query Parameters ====================


class CampaignListParams(BaseModel):
    """Query parameters for campaign listing."""

    state: CampaignState | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    owner_id: UUID | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class HistoryListParams(BaseModel):
    """Query parameters for history listing."""

    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)
