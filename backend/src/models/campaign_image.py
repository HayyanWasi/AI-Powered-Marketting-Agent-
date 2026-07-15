from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field


class CampaignContext(BaseModel):
    """Optional context for the campaign."""

    platform: str | None = Field(
        default=None,
        description="Target platform for the campaign",
        examples=["instagram", "linkedin", "facebook", "twitter", "tiktok", "youtube"],
    )
    campaign_type: str | None = Field(
        default=None,
        description="Type of campaign",
        examples=[
            "seasonal_sale",
            "product_launch",
            "brand_awareness",
            "event_promotion",
            "lead_generation",
        ],
    )
    target_audience: str | None = Field(
        default=None,
        description="Description of target audience",
    )


class CampaignImageRequest(BaseModel):
    """Request payload for generating a campaign image."""

    company_profile_id: UUID = Field(
        ..., description="UUID of the company profile for brand context"
    )
    campaign_prompt: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Natural language description of the campaign image to generate",
    )
    campaign_context: CampaignContext | None = Field(
        default=None,
        description="Optional context for the campaign",
    )


class ValidationResult(BaseModel):
    """Result of image validation."""

    width: int = Field(..., ge=0, description="Image width in pixels")
    height: int = Field(..., ge=0, description="Image height in pixels")
    passed: bool = Field(..., description="Whether validation passed")


class CampaignImageResponse(BaseModel):
    """Response payload after successful image generation."""

    image_url: str = Field(..., description="Direct CDN URL to the generated image (Pollinations)")
    model: str = Field(..., description="Pollinations model used", examples=["kontext"])
    generation_time_ms: int = Field(
        ..., ge=0, description="Total generation time including retries"
    )
    fallback_used: bool = Field(..., description="Whether fallback mechanism was activated")
    brand_applied: bool = Field(..., description="Whether brand styling was applied")
    validation: ValidationResult = Field(..., description="Image validation results")


@dataclass
class CompanyProfile:
    """Company profile from Supabase."""

    id: str
    name: str
    brand_colors: list[str] | None = None
    brand_personality: str | None = None
    style_guide: str | None = None
    logo_url: str | None = None
    typography_style: str | None = None
    reference_images: list[str] | None = None
    industry_category: str | None = None
    created_at: str = ""
    updated_at: str = ""
