"""Models package - domain entities and Pydantic schemas."""

from .campaign import (
    AssetSource,
    AssetType,
    Campaign,
    CampaignAsset,
    CampaignState,
    Goals,
    Schedule,
    TargetAudience,
)
from .errors import (
    CampaignError,
    DuplicateNameError,
    NotFoundError,
    PreconditionFailedError,
    StateTransitionError,
    ValidationError,
    VersionConflictError,
)
from .history import CampaignHistoryEntry, EventType
from .schemas import (
    AssetContent,
    AssetListResponse,
    AssetResponse,
    # Query params
    CampaignListParams,
    CampaignListResponse,
    CampaignResponse,
    CampaignSummary,
    # Assets
    CopyContent,
    CreateAssetRequest,
    # Campaign
    CreateCampaignRequest,
    # Errors
    ErrorResponse,
    HashtagSetContent,
    HistoryEntryResponse,
    HistoryListParams,
    # History
    HistoryListResponse,
    ImageContent,
    MetadataContent,
    Platform,
    # State Transition
    StateTransitionRequest,
    StateTransitionResponse,
    UpdateCampaignRequest,
)
from .schemas import (
    # Enums
    CampaignState as SchemaCampaignState,
)
from .schemas import (
    EventType as SchemaEventType,
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
