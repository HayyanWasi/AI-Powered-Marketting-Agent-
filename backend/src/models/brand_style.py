from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class BrandStyleContext(BaseModel):
    """Extracted and formatted brand attributes for prompt conditioning. Not persisted."""

    color_palette: str | None = Field(
        default=None,
        description="Comma-separated hex color codes for prompt",
        examples=["#FF6B35, #004E89"],
    )
    personality_descriptors: str | None = Field(
        default=None,
        description="Brand personality descriptors for prompt",
        examples=["modern, professional, innovative"],
    )
    style_guidance: str | None = Field(
        default=None,
        description="Style guide text for prompt",
        examples=["Clean lines, ample whitespace, modern typography"],
    )
    logo_reference: str | None = Field(
        default=None,
        description="Logo description or URL for prompt",
        examples=["Abstract geometric mark in brand orange"],
    )
    reference_image_urls: list[str] = Field(
        default_factory=list,
        description="URLs of brand reference images",
        examples=[["https://storage.supabase.co/brand/ref1.jpg"]],
    )


@dataclass
class BrandStyleContextInternal:
    """Internal dataclass for brand style context (used in services)."""

    color_palette: str | None = None
    personality_descriptors: str | None = None
    style_guidance: str | None = None
    logo_reference: str | None = None
    reference_image_urls: list[str] = field(default_factory=list)

    def to_model(self) -> BrandStyleContext:
        """Convert to Pydantic model."""
        return BrandStyleContext(
            color_palette=self.color_palette,
            personality_descriptors=self.personality_descriptors,
            style_guidance=self.style_guidance,
            logo_reference=self.logo_reference,
            reference_image_urls=self.reference_image_urls,
        )


@dataclass
class PollinationsPrompt:
    """Complete prompt sent to Pollinations API."""

    base_prompt: str
    model: str = "kontext"
    negative_prompt: str | None = None

    def to_url_params(self) -> dict[str, str]:
        """Convert to URL parameters for Pollinations API."""
        params = {"model": self.model}
        if self.negative_prompt:
            params["negative_prompt"] = self.negative_prompt
        return params
