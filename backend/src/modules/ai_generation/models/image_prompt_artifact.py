"""Image prompt artifact model for AI Generation Engine."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ImagePromptArtifact:
    """
    Structured image prompt derived from approved Copy and Strategy Artifacts.
    Ready for image generation.
    """

    id: str
    generated_at: datetime
    strategy_id: str
    copy_id: str
    platform: str
    prompt_text: str
    style_guidelines: Dict[str, Any]
    brand_elements: List[Dict[str, Any]]
    visual_elements: List[Dict[str, Any]]
    composition_guidelines: Dict[str, Any]
    validation_results: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize prompt to dictionary for storage/transmission."""
        return {
            "id": self.id,
            "generated_at": self.generated_at.isoformat(),
            "strategy_id": self.strategy_id,
            "copy_id": self.copy_id,
            "platform": self.platform,
            "prompt_text": self.prompt_text,
            "style_guidelines": self.style_guidelines,
            "brand_elements": self.brand_elements,
            "visual_elements": self.visual_elements,
            "composition_guidelines": self.composition_guidelines,
            "validation_results": self.validation_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImagePromptArtifact":
        """Deserialize prompt from dictionary."""
        return cls(
            id=data["id"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            strategy_id=data["strategy_id"],
            copy_id=data["copy_id"],
            platform=data["platform"],
            prompt_text=data["prompt_text"],
            style_guidelines=data["style_guidelines"],
            brand_elements=data["brand_elements"],
            visual_elements=data["visual_elements"],
            composition_guidelines=data["composition_guidelines"],
            validation_results=data.get("validation_results"),
        )
