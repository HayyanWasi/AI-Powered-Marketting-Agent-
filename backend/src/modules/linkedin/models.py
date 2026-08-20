"""Pydantic models for LinkedIn Campaign Execution & Auto-Pilot Engine."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class PostStatus(str, Enum):
    """Lifecycle status of a LinkedIn feed post."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class SequenceStatus(str, Enum):
    """Status of a lead's outreach sequence."""

    PENDING = "pending"
    VISITING = "visiting"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    REPLIED = "replied"
    WITHDRAWN = "withdrawn"
    COMPLETED = "completed"
    FAILED = "failed"


class AutoPilotConfig(BaseModel):
    """Per-campaign safety & execution limits (User-configurable on Launchpad)."""

    model_config = ConfigDict(frozen=True)

    daily_invite_limit: int = Field(default=20, ge=1, le=50)
    daily_message_limit: int = Field(default=30, ge=1, le=100)
    delay_min_seconds: int = Field(default=90, ge=30, le=600)
    delay_max_seconds: int = Field(default=210, ge=60, le=1200)
    withdraw_after_days: int = Field(default=7, ge=1, le=30)
    business_hours_start: int = Field(default=9, ge=0, le=23)
    business_hours_end: int = Field(default=18, ge=0, le=23)
    stop_on_reply: bool = True
    timezone: str = "Asia/Karachi"
    min_evidence_confidence: float = Field(default=3.5, ge=1.0, le=5.0)


class ResearchedFact(BaseModel):
    """A single web-verified claim/quote extracted from ResearchBrief."""

    model_config = ConfigDict(frozen=True)

    fact_id: str = Field(default_factory=lambda: f"fact_{uuid4().hex[:8]}")
    dimension: str  # market, competitor, audience, content, channel, trend
    claim: str
    quote: str = ""
    source_url: str = ""
    confidence_score: float = 4.0


class ContentContext(BaseModel):
    """Data payload passed to LLM for research-grounded post generation."""

    model_config = ConfigDict(frozen=True)

    slot_id: str
    slot_date: str
    scheduled_time: str = "09:00 AM"
    theme: str
    messaging_pillar: str
    cta: str
    phase: str = "launch"
    format_type: str = "Text Post"
    tone_of_voice: str = "Professional & Data-driven"

    # MUST be sourced from web research
    researched_facts: tuple[ResearchedFact, ...] = ()

    # Strategic anchors from approved plan
    differentiation_angle: str = ""
    usp: str = ""
    guest_name: str | None = None
    guest_position: str | None = None
    guest_organization: str | None = None
    guest_profile: dict | None = None

    # Event / intake data — loaded from intake_checklists
    event_name: str = ""
    event_date: str = ""
    venue: str = ""
    registration_link: str = ""
    target_audience: str = ""
    curriculum_breakdown: str = ""
    ticket_price: str = "Free"


class LinkedInPost(BaseModel):
    """Generated LinkedIn post ready for preview & scheduling."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    slot_id: str
    scheduled_at: datetime
    hook: str
    body: str
    cta_text: str
    full_content: str
    evidence_ids: tuple[str, ...] = ()
    status: PostStatus = PostStatus.DRAFT
    unipile_post_id: str | None = None
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump(mode="json")
        return d


class OutreachStep(BaseModel):
    """Single step in the outbound sequence."""

    model_config = ConfigDict(frozen=True)

    step_number: int
    action_type: str  # visit_profile, send_invite, send_value_msg, send_followup
    delay_hours: int = 0
    message_template: str = ""
    description: str = ""


class OutreachTemplate(BaseModel):
    """4-step outbound sequence template."""

    model_config = ConfigDict(frozen=True)

    campaign_id: UUID
    step_invite_msg: str = ""
    step_value_msg: str = ""
    step_followup_msg: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LinkedInAccount(BaseModel):
    """Connected LinkedIn Account metadata."""

    model_config = ConfigDict(frozen=True)

    account_id: UUID = Field(default_factory=uuid4)
    organization_id: UUID | None = None
    unipile_account_id: str
    display_name: str = ""
    profile_url: str = ""
    status: str = "active"
    connected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LaunchpadPreview(BaseModel):
    """Data structure returned to frontend Campaign Launchpad screen."""

    model_config = ConfigDict(frozen=True)

    campaign_id: UUID
    campaign_name: str
    autopilot_config: AutoPilotConfig
    posts: tuple[LinkedInPost, ...] = ()
    outreach_template: OutreachTemplate | None = None
    connected_account: LinkedInAccount | None = None
    status: str = "draft"
