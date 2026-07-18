"""Strategy artifact model for AI Generation Engine."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StrategyArtifact:
    """
    Structured campaign strategy produced from the Generation Context.
    Defines the foundation for subsequent content generation.
    """

    id: str
    generated_at: datetime
    audience_strategy: Dict[str, Any]
    messaging_strategy: Dict[str, Any]
    platform_strategy: Dict[str, Any]
    seo_strategy: Dict[str, Any]
    campaign_strategy: Dict[str, Any]
    validation_results: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize strategy to dictionary for storage/transmission."""
        return {
            "id": self.id,
            "generated_at": self.generated_at.isoformat(),
            "audience_strategy": self.audience_strategy,
            "messaging_strategy": self.messaging_strategy,
            "platform_strategy": self.platform_strategy,
            "seo_strategy": self.seo_strategy,
            "campaign_strategy": self.campaign_strategy,
            "validation_results": self.validation_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyArtifact":
        """Deserialize strategy from dictionary."""
        return cls(
            id=data["id"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            audience_strategy=data["audience_strategy"],
            messaging_strategy=data["messaging_strategy"],
            platform_strategy=data["platform_strategy"],
            seo_strategy=data["seo_strategy"],
            campaign_strategy=data["campaign_strategy"],
            validation_results=data.get("validation_results"),
        )
