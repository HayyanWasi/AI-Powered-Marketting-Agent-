"""Campaign domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class CampaignState(str, Enum):
    """Valid campaign lifecycle states."""

    DRAFT = "Draft"
    READY = "Ready"
    REVIEW = "Review"
    APPROVED = "Approved"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"


# Valid state transitions
VALID_TRANSITIONS = {
    CampaignState.DRAFT: [CampaignState.READY, CampaignState.ARCHIVED],
    CampaignState.READY: [CampaignState.REVIEW, CampaignState.DRAFT, CampaignState.ARCHIVED],
    CampaignState.REVIEW: [CampaignState.APPROVED, CampaignState.READY, CampaignState.ARCHIVED],
    CampaignState.APPROVED: [CampaignState.PUBLISHED, CampaignState.REVIEW, CampaignState.ARCHIVED],
    CampaignState.PUBLISHED: [CampaignState.ARCHIVED],
    CampaignState.ARCHIVED: [
        CampaignState.DRAFT,
        CampaignState.READY,
        CampaignState.REVIEW,
        CampaignState.APPROVED,
        CampaignState.PUBLISHED,
    ],
}


@dataclass
class Goals:
    """Structured campaign goals."""

    primary: str
    metrics: List[str] = field(default_factory=list)
    targets: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary,
            "metrics": self.metrics,
            "targets": self.targets,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goals":
        return cls(
            primary=data.get("primary", ""),
            metrics=data.get("metrics", []),
            targets=data.get("targets", {}),
        )


@dataclass
class TargetAudience:
    """Target audience definition."""

    segments: List[str] = field(default_factory=list)
    demographics: Dict[str, Any] = field(default_factory=dict)
    interests: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segments": self.segments,
            "demographics": self.demographics,
            "interests": self.interests,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TargetAudience":
        return cls(
            segments=data.get("segments", []),
            demographics=data.get("demographics", {}),
            interests=data.get("interests", []),
        )


@dataclass
class Schedule:
    """Campaign schedule."""

    start_date: datetime
    end_date: datetime
    timezone: str
    recurrence_rule: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "timezone": self.timezone,
            "recurrence_rule": self.recurrence_rule,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Schedule":
        return cls(
            start_date=(
                datetime.fromisoformat(data["start_date"])
                if data.get("start_date")
                else datetime.utcnow()
            ),
            end_date=(
                datetime.fromisoformat(data["end_date"])
                if data.get("end_date")
                else datetime.utcnow()
            ),
            timezone=data.get("timezone", "UTC"),
            recurrence_rule=data.get("recurrence_rule"),
        )


@dataclass
class Campaign:
    """Core campaign entity."""

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    company_profile_id: Optional[UUID] = None
    name: str = ""
    goals: Optional[Goals] = None
    target_audience: Optional[TargetAudience] = None
    platforms: List[str] = field(default_factory=list)
    schedule: Optional[Schedule] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: CampaignState = CampaignState.DRAFT
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_by: UUID = field(default_factory=uuid4)
    updated_by: UUID = field(default_factory=uuid4)
    previous_state: Optional[CampaignState] = None  # For archive/restore

    def to_dict(self) -> Dict[str, Any]:
        """Serialize campaign to dictionary for storage/history."""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "company_profile_id": str(self.company_profile_id) if self.company_profile_id else None,
            "name": self.name,
            "goals": self.goals.to_dict() if self.goals else None,
            "target_audience": self.target_audience.to_dict() if self.target_audience else None,
            "platforms": self.platforms,
            "schedule": self.schedule.to_dict() if self.schedule else None,
            "metadata": self.metadata,
            "state": self.state.value,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "created_by": str(self.created_by),
            "updated_by": str(self.updated_by),
            "previous_state": self.previous_state.value if self.previous_state else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Campaign":
        """Deserialize campaign from dictionary."""
        campaign = cls(
            id=UUID(data["id"]),
            organization_id=UUID(data["organization_id"]),
            company_profile_id=(
                UUID(data["company_profile_id"]) if data.get("company_profile_id") else None
            ),
            name=data.get("name", ""),
            platforms=data.get("platforms", []),
            metadata=data.get("metadata", {}),
            state=CampaignState(data["state"]),
            version=data.get("version", 1),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.utcnow()
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if data.get("updated_at")
                else datetime.utcnow()
            ),
            published_at=(
                datetime.fromisoformat(data["published_at"]) if data.get("published_at") else None
            ),
            archived_at=(
                datetime.fromisoformat(data["archived_at"]) if data.get("archived_at") else None
            ),
            created_by=UUID(data["created_by"]),
            updated_by=UUID(data["updated_by"]),
            previous_state=(
                CampaignState(data["previous_state"]) if data.get("previous_state") else None
            ),
        )

        # Parse nested objects
        if data.get("goals"):
            campaign.goals = Goals.from_dict(data["goals"])
        if data.get("target_audience"):
            campaign.target_audience = TargetAudience.from_dict(data["target_audience"])
        if data.get("schedule"):
            campaign.schedule = Schedule.from_dict(data["schedule"])

        return campaign

    @property
    def can_edit_config(self) -> bool:
        """Check if configuration can be edited."""
        return self.state == CampaignState.DRAFT

    @property
    def is_active(self) -> bool:
        """Check if campaign is active (not archived)."""
        return self.state != CampaignState.ARCHIVED


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


@dataclass
class CampaignAsset:
    """Asset associated with a campaign."""

    id: UUID = field(default_factory=uuid4)
    campaign_id: UUID = field(default_factory=uuid4)
    asset_type: AssetType = AssetType.COPY
    content: Dict[str, Any] = field(default_factory=dict)
    storage_path: Optional[str] = None
    source: AssetSource = AssetSource.MANUAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: UUID = field(default_factory=uuid4)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize asset to dictionary for storage."""
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id),
            "asset_type": self.asset_type.value,
            "content": self.content,
            "storage_path": self.storage_path,
            "source": self.source.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": str(self.created_by),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignAsset":
        """Deserialize asset from dictionary."""
        return cls(
            id=UUID(data["id"]),
            campaign_id=UUID(data["campaign_id"]),
            asset_type=AssetType(data["asset_type"]),
            content=data.get("content", {}),
            storage_path=data.get("storage_path"),
            source=AssetSource(data["source"]),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.utcnow()
            ),
            created_by=UUID(data["created_by"]),
        )
