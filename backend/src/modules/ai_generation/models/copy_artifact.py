"""Copy artifact model for AI Generation Engine."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CopyArtifact:
    """
    Platform-specific marketing copy generated from the Strategy Artifact.
    Contains platform-adapted content.
    """

    id: str
    generated_at: datetime
    strategy_id: str
    platform: str
    headlines: list[str]
    captions: list[str]
    ctas: list[str]
    hashtags: list[str]
    content_blocks: list[dict[str, Any]] = field(default_factory=list)
    validation_results: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize copy to dictionary for storage/transmission."""
        return {
            "id": self.id,
            "generated_at": self.generated_at.isoformat(),
            "strategy_id": self.strategy_id,
            "platform": self.platform,
            "headlines": self.headlines,
            "captions": self.captions,
            "ctas": self.ctas,
            "hashtags": self.hashtags,
            "content_blocks": self.content_blocks,
            "validation_results": self.validation_results,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CopyArtifact":
        """Deserialize copy from dictionary."""
        return cls(
            id=data["id"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            strategy_id=data["strategy_id"],
            platform=data["platform"],
            headlines=data["headlines"],
            captions=data["captions"],
            ctas=data["ctas"],
            hashtags=data["hashtags"],
            content_blocks=data.get("content_blocks", []),
            validation_results=data.get("validation_results"),
        )
