"""Generation context model for AI Generation Engine."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GenerationContext:
    """
    Complete campaign context assembled before generation begins.
    Serves as the single source of truth for all generation stages.
    """

    campaign_context: Dict[str, Any]
    company_profile: Dict[str, Any]
    audience: Dict[str, Any]
    platforms: List[str]
    brand_guidelines: Dict[str, Any]
    reference_materials: List[Dict[str, Any]]
    user_intent: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
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
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationContext":
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
