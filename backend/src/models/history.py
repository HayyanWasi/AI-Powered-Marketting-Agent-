"""Campaign history model."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from src.models.campaign import CampaignState


class EventType(str, Enum):
    """History event types."""

    CREATED = "Created"
    CONFIGURATION_CHANGED = "ConfigurationChanged"
    STATE_TRANSITIONED = "StateTransitioned"
    ASSET_ASSOCIATED = "AssetAssociated"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"
    RESTORED = "Restored"


@dataclass
class CampaignHistoryEntry:
    """Immutable audit log entry for campaign changes."""

    id: UUID = field(default_factory=uuid4)
    campaign_id: UUID = field(default_factory=uuid4)
    event_type: EventType = EventType.CREATED
    timestamp: datetime = field(default_factory=datetime.utcnow)
    actor_id: UUID = field(default_factory=uuid4)
    from_state: Optional[CampaignState] = None
    to_state: Optional[CampaignState] = None
    changed_fields: Optional[Dict[str, Any]] = None
    snapshot: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id),
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "actor_id": str(self.actor_id),
            "from_state": self.from_state.value if self.from_state else None,
            "to_state": self.to_state.value if self.to_state else None,
            "changed_fields": self.changed_fields,
            "snapshot": self.snapshot,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignHistoryEntry":
        """Deserialize from dictionary."""
        entry = cls(
            id=UUID(data["id"]),
            campaign_id=UUID(data["campaign_id"]),
            event_type=EventType(data["event_type"]),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if data.get("timestamp")
                else datetime.utcnow()
            ),
            actor_id=UUID(data["actor_id"]),
            from_state=CampaignState(data["from_state"]) if data.get("from_state") else None,
            to_state=CampaignState(data["to_state"]) if data.get("to_state") else None,
            changed_fields=data.get("changed_fields"),
            snapshot=data.get("snapshot"),
            metadata=data.get("metadata"),
        )
        return entry
