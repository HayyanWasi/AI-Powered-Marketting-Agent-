"""Generation context model for AI Generation Engine."""

from dataclasses import dataclass
from typing import Any


@dataclass
class GenerationContext:
    """
    Complete campaign context assembled before generation begins.
    Serves as the single source of truth for all generation stages.
    """

    campaign_context: dict[str, Any]
    company_profile: dict[str, Any]
    audience: dict[str, Any]
    platforms: list[str]
    brand_guidelines: dict[str, Any]
    reference_materials: list[dict[str, Any]]
    user_intent: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize context to dictionary for storage/transmission."""
        return {
            "campaign_context": self.campaign_context,
            "company_profile": self.company_profile,
            "audience": self.audience,
            "platforms": self.platforms,
            "brand_guidelines": self.brand_guidelines,
            "reference_materials": self.reference_materials,
            "user_intent": self.user_intent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenerationContext":
        """Deserialize context from dictionary."""
        return cls(
            campaign_context=data["campaign_context"],
            company_profile=data["company_profile"],
            audience=data["audience"],
            platforms=data["platforms"],
            brand_guidelines=data["brand_guidelines"],
            reference_materials=data["reference_materials"],
            user_intent=data.get("user_intent"),
        )
