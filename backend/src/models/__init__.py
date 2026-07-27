"""Models package - domain entities and Pydantic schemas."""

from .campaign import (
    Campaign,
    CampaignState,
    Goals,
    TargetAudience,
    Schedule,
    CampaignAsset,
    AssetType,
    AssetSource,
)
from .history import CampaignHistoryEntry, EventType
from .errors import (
    CampaignError,
    StateTransitionError,
    VersionConflictError,
    NotFoundError,
    DuplicateNameError,
    ValidationError,
    PreconditionFailedError,
)
from .schemas import (
    # Enums
    CampaignState as SchemaCampaignState,
    EventType as SchemaEventType,
    AssetType,
    AssetSource,
    Platform,
    # Campaign
    CreateCampaignRequest,
    UpdateCampaignRequest,
    CampaignResponse,
    CampaignSummary,
    CampaignListResponse,
    # State Transition
    StateTransitionRequest,
    StateTransitionResponse,
    HistoryEntryResponse,
    # History
    HistoryListResponse,
    # Assets
    CopyContent,
    ImageContent,
    HashtagSetContent,
    MetadataContent,
    AssetContent,
    CreateAssetRequest,
    AssetResponse,
    AssetListResponse,
    # Query params
    CampaignListParams,
    HistoryListParams,
    # Errors
    ErrorResponse,
)

__all__ = [
    # Domain models
    "Campaign",
    "CampaignState",
    "Goals",
    "TargetAudience",
    "Schedule",
    "CampaignAsset",
    "AssetType",
    "AssetSource",
    "CampaignHistoryEntry",
    "EventType",
    # Exceptions
    "CampaignError",
    "StateTransitionError",
    "VersionConflictError",
    "NotFoundError",
    "DuplicateNameError",
    "ValidationError",
    "PreconditionFailedError",
    # Schemas
    "SchemaCampaignState",
    "SchemaEventType",
    "AssetType",
    "AssetSource",
    "Platform",
    "CreateCampaignRequest",
    "UpdateCampaignRequest",
    "CampaignResponse",
    "CampaignSummary",
    "CampaignListResponse",
    "StateTransitionRequest",
    "StateTransitionResponse",
    "HistoryEntryResponse",
    "HistoryListResponse",
    "CopyContent",
    "ImageContent",
    "HashtagSetContent",
    "MetadataContent",
    "AssetContent",
    "CreateAssetRequest",
    "AssetResponse",
    "AssetListResponse",
    "CampaignListParams",
    "HistoryListParams",
    "ErrorResponse",
]
