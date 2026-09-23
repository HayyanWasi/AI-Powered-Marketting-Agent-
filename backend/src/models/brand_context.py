"""Canonical, immutable company identity used by planning and LinkedIn generation."""

import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.company import CompanyProfile


class BrandGuidelinesSchema(BaseModel):
    """Versioned schema for brand guidelines preserving legacy and unknown fields."""

    model_config = ConfigDict(extra="allow")

    schemaVersion: int = 2
    legacyProse: str = ""
    website: str = ""
    industry: str = ""
    description: str = ""
    targetAudience: str = ""
    trackRecord: str = ""
    specializations: list[str] = Field(default_factory=list)
    toneMessage: str = ""
    selectedTraits: list[str] = Field(default_factory=list)
    sampleMessage: str = ""
    negativeGuardrails: list[str] = Field(default_factory=list)

    @classmethod
    def parse_and_migrate(cls, raw: str) -> "BrandGuidelinesSchema":
        if not raw or not raw.strip():
            return cls()
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return cls(legacyProse=raw)
        except (ValueError, TypeError):
            return cls(legacyProse=raw)

        # Merge dict into schema, extra fields will be preserved
        # Ensure schemaVersion is 2
        data["schemaVersion"] = 2
        return cls(**data)

    def merge_update(self, new_raw: str) -> str:
        """Merge a new JSON string into the current schema without destroying unknowns."""
        if not new_raw or not new_raw.strip():
            return self.model_dump_json()

        try:
            new_data = json.loads(new_raw)
            if not isinstance(new_data, dict):
                self.legacyProse = new_raw
                return self.model_dump_json()
        except (ValueError, TypeError):
            self.legacyProse = new_raw
            return self.model_dump_json()

        current_dict = self.model_dump()
        current_dict.update(new_data)
        current_dict["schemaVersion"] = 2

        return json.dumps(current_dict)


class BrandContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    company_profile_id: UUID
    company_name: str
    profile_updated_at: str = ""
    website: str = ""
    industry: str = ""
    description: str = ""
    target_audience: str = ""
    track_record: str = ""
    specializations: tuple[str, ...] = ()
    brand_tone: str = ""
    personality_traits: tuple[str, ...] = ()
    sample_voice: str = ""
    guidelines: str = ""
    negative_guardrails: tuple[str, ...] = ()
    reference_image_urls: tuple[str, ...] = ()

    @classmethod
    def from_profile(cls, profile: CompanyProfile) -> "BrandContext":
        """Read only real BrandProfileData keys; retain legacy prose without guessing."""
        raw = profile.brand_guidelines
        schema = BrandGuidelinesSchema.parse_and_migrate(raw)
        data = schema.model_dump()

        def text(key: str) -> str:
            value = data.get(key)
            return value.strip() if isinstance(value, str) else ""

        def strings(key: str) -> tuple[str, ...]:
            value = data.get(key)
            if not isinstance(value, list):
                return ()
            return tuple(v.strip() for v in value if isinstance(v, str) and v.strip())

        return cls(
            company_profile_id=UUID(profile.id),
            company_name=profile.company_name,
            profile_updated_at=profile.updated_at,
            website=text("website"),
            industry=text("industry"),
            description=text("description"),
            target_audience=text("targetAudience"),
            track_record=text("trackRecord"),
            specializations=strings("specializations"),
            brand_tone=profile.brand_tone or text("toneMessage"),
            personality_traits=strings("selectedTraits"),
            sample_voice=text("sampleMessage"),
            guidelines=text("legacyProse"),
            negative_guardrails=strings("negativeGuardrails"),
            reference_image_urls=tuple(profile.reference_image_urls),
        )

    def as_prompt(self) -> str:
        """One rendering used by every active generation prompt."""
        fields = {
            "Company": self.company_name,
            "Website": self.website,
            "Industry": self.industry,
            "Company description": self.description,
            "Brand audience": self.target_audience,
            "Track record": self.track_record,
            "Specializations": "; ".join(self.specializations),
            "Brand tone / writing style": self.brand_tone,
            "Personality traits": "; ".join(self.personality_traits),
            "Sample voice": self.sample_voice,
            "Brand guidelines": self.guidelines,
            "Do not / guardrails": "; ".join(self.negative_guardrails),
        }
        return "\n".join(f"{label}: {value}" for label, value in fields.items() if value)
