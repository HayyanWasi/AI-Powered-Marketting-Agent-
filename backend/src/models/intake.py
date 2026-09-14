"""Pydantic schemas and models for Conversational Campaign Intake."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class IntakeChecklist(BaseModel):
    """Structured checklist tracking collected campaign details."""

    model_config = ConfigDict(extra="ignore")

    event_name: str | None = None
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
    target_audience: str | None = None
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

        core_required = [
            self.event_name,
            self.category,
            self.target_audience,
            self.event_date,
            self.venue,
            self.curriculum_breakdown,
            self.outcome_deliverable,
            self.is_free_or_paid,
        ]
        has_core = all(_valid(x) for x in core_required)

        guest_ok = True
        if self.has_guest is True:
            guest_ok = _valid(self.guest_name) and self.guest_confirmed

        return has_core and guest_ok


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

    event_name: str | None = None
    category: str | None = None
    event_date: str | None = None
    venue: str | None = None
    has_guest: bool | None = None
    guest_name: str | None = None
    guest_title: str | None = None
    curriculum_breakdown: str | None = None
    outcome_deliverable: str | None = None
    is_free_or_paid: str | None = None
    registration_link: str | None = None
    target_audience: str | None = None


class UnifiedIntakeResponse(BaseModel):
    """The final, strict JSON structure the LLM MUST return on every single turn."""

    extracted: ExtractedData = Field(
        description="The campaign data found in the user's latest message. Leave missing fields as null."
    )
    reply: str = Field(
        description="A friendly conversational reply asking the user for the NEXT 2-3 missing fields."
    )
