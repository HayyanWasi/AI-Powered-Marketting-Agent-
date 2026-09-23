"""Pydantic schemas and models for Conversational Campaign Intake."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.models.audience import AudienceProfile


class CampaignType(str, Enum):
    APP_LAUNCH = "app_launch"
    PRODUCT_LAUNCH = "product_launch"
    SERVICE_LAUNCH = "service_launch"
    PHYSICAL_EVENT = "physical_event"
    WEBINAR = "webinar"
    GENERAL_PROMOTION = "general_promotion"


class IntakeChecklist(BaseModel):
    """Structured checklist tracking collected campaign details."""

    model_config = ConfigDict(extra="ignore")

    campaign_type: CampaignType | None = None
    campaign_name: str | None = None  # Replaces/generalizes event_name/product_name
    objective: str | None = None
    target_audience: str | None = None
    audience_profile: AudienceProfile | None = None
    audience_profile_version: str | None = None
    value_proposition: str | None = None
    cta_url: str | None = None

    # Campaign scheduling validity window (ISO YYYY-MM-DD). This is the range the
    # campaign is allowed to schedule within — NOT the date of an actual event.
    # When confirmed, these become the authoritative campaign.schedule bounds.
    campaign_start_date: str | None = None
    campaign_end_date: str | None = None

    # Event-specific
    event_date: str | None = None  # Resolved ISO YYYY-MM-DD
    venue: str | None = None
    has_guest: bool | None = None
    guest_name: str | None = None
    guest_title: str | None = None
    guest_confirmed: bool = False
    curriculum_breakdown: str | None = None
    outcome_deliverable: str | None = None
    is_free_or_paid: str | None = None
    registration_link: str | None = None

    category: str | None = None
    guest_profile: dict[str, Any] | None = None
    last_field_asked: str | None = None

    def is_complete(self) -> bool:
        """Check if baseline required fields are collected."""

        def _valid(val: str | None) -> bool:
            return bool(
                val
                and str(val).strip()
                and str(val).strip().lower() not in ("null", "none", "n/a", "undefined")
            )

        if not _valid(self.campaign_type):
            return False

        resolved_audience = self.target_audience or (
            self.audience_profile.summary if self.audience_profile and self.audience_profile.is_usable() else None
        )
        common_required = [self.campaign_name, self.objective, resolved_audience]
        has_common = all(_valid(x) for x in common_required)

        if self.campaign_type in (
            CampaignType.APP_LAUNCH,
            CampaignType.PRODUCT_LAUNCH,
            CampaignType.SERVICE_LAUNCH,
            CampaignType.GENERAL_PROMOTION,
        ):
            type_required = [self.value_proposition]
            return has_common and all(_valid(x) for x in type_required)

        elif self.campaign_type in (CampaignType.PHYSICAL_EVENT, CampaignType.WEBINAR):
            type_required = [self.event_date, self.venue]
            has_type = all(_valid(x) for x in type_required)

            guest_ok = True
            if self.has_guest is True:
                guest_ok = _valid(self.guest_name) and self.guest_confirmed

            return has_common and has_type and guest_ok

        return False


class IntakeMessage(BaseModel):
    """Single turn in the intake conversation."""

    model_config = ConfigDict(extra="ignore")

    id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    role: str  # 'user', 'assistant', 'system'
    content: str
    language: str = "en"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntakeChatRequest(BaseModel):
    """Incoming user payload for intake chat."""

    campaign_id: UUID
    user_message: str
    language: str = "en"


class IntakeChatResponse(BaseModel):
    """Outgoing response payload from intake chat."""

    campaign_id: UUID
    reply: str
    language: str
    checklist: IntakeChecklist
    is_complete: bool
    guest_confirmation_needed: bool = False
    guest_detected: dict[str, str] | None = None


class GuestConfirmRequest(BaseModel):
    """Payload to confirm or edit detected guest information."""

    campaign_id: UUID
    guest_name: str
    guest_title: str | None = None
    confirmed: bool = True


class ExtractedData(BaseModel):
    """The raw campaign data extracted from the user's message."""

    model_config = ConfigDict(extra="ignore")

    # Kept as a free string: providers emit human wording ("General Promotion").
    # Canonicalisation to CampaignType happens in the intake service, which fails
    # truthfully when a non-empty value cannot be resolved.
    campaign_type: str | None = None
    campaign_name: str | None = None
    objective: str | None = None
    target_audience: str | None = None
    audience_profile: AudienceProfile | None = None
    audience_profile_version: str | None = None
    value_proposition: str | None = None
    cta_url: str | None = None

    # Campaign scheduling validity window (ISO YYYY-MM-DD) — distinct from
    # event_date, which is an actual event/webinar date.
    campaign_start_date: str | None = None
    campaign_end_date: str | None = None

    event_date: str | None = None
    venue: str | None = None
    has_guest: bool | None = None
    guest_name: str | None = None
    guest_title: str | None = None
    curriculum_breakdown: str | None = None
    outcome_deliverable: str | None = None
    is_free_or_paid: str | None = None
    registration_link: str | None = None
    category: str | None = None


class UnifiedIntakeResponse(BaseModel):
    """The final, strict JSON structure the LLM MUST return on every single turn."""

    model_config = ConfigDict(extra="ignore")

    extracted: ExtractedData = Field(
        description="The campaign data found in the user's latest message. Leave missing fields as null."
    )
    reply: str = Field(
        description="A friendly conversational reply asking the user for the NEXT 2-3 missing fields."
    )
