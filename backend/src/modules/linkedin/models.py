"""Pydantic models for LinkedIn Campaign Execution & Auto-Pilot Engine."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.models.brand_context import BrandContext

# ── Enums ────────────────────────────────────────────────────────────────────


class PostStatus(StrEnum):
    """Lifecycle status of a LinkedIn feed post."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    # Transient claim state: a worker has atomically taken this post and is
    # publishing it. Guarantees exactly-once dispatch across workers/processes.
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    # Fail-closed recovery state: a claim that stayed in 'publishing' past the
    # stale threshold (worker likely crashed mid-publish). Because this Unipile
    # deployment cannot reconcile whether the remote post was created, such a
    # row is NEVER auto-republished — it is parked here for manual review.
    NEEDS_REVIEW = "needs_review"


class SequenceStatus(StrEnum):
    """Status of a lead's outreach sequence."""

    PENDING = "pending"
    VISITING = "visiting"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    REPLIED = "replied"
    WITHDRAWN = "withdrawn"
    COMPLETED = "completed"
    FAILED = "failed"


class WarmupPhase(StrEnum):
    """Account warm-up lifecycle phase."""

    BASELINE = "baseline"
    RAMP_UP = "ramp_up"
    OPERATING = "operating"


class ReviewStatus(StrEnum):
    """Review gate status for AI-generated engagement content."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    EXPIRED = "expired"


class CircuitState(StrEnum):
    """Circuit breaker state machine."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ── AutoPilot Config ─────────────────────────────────────────────────────────


class AutoPilotConfig(BaseModel):
    """Per-campaign safety & execution limits (User-configurable on Launchpad).

    Target personas are NOT stored here — they live in the
    ``linkedin_target_personas`` database table for dynamic management.
    """

    model_config = ConfigDict(frozen=True)

    # ── Outreach limits ──
    daily_invite_limit: int = Field(default=25, ge=1, le=50)
    daily_message_limit: int = Field(default=30, ge=1, le=100)

    # ── Engagement limits ──
    daily_like_limit: int = Field(default=40, ge=1, le=50)
    daily_comment_limit: int = Field(default=15, ge=1, le=30)

    # ── Delay bounds (used by RateLimiter) ──
    delay_min_seconds: int = Field(default=40, ge=20, le=600)
    delay_max_seconds: int = Field(default=180, ge=60, le=1200)

    # ── Sequence management ──
    withdraw_after_days: int = Field(default=7, ge=1, le=30)
    stop_on_reply: bool = True

    # ── Flexible work window (human-like variance) ──
    work_start_earliest: int = Field(default=8, ge=6, le=10)
    work_start_latest: int = Field(default=9, ge=7, le=11)
    work_end_earliest: int = Field(default=16, ge=14, le=18)
    work_end_latest: int = Field(default=17, ge=15, le=19)

    # ── Lunch dead zone ──
    lunch_start_earliest: int = Field(default=12, ge=11, le=13)
    lunch_start_latest: int = Field(default=13, ge=12, le=14)
    lunch_duration_min_minutes: int = Field(default=45, ge=30, le=90)
    lunch_duration_max_minutes: int = Field(default=90, ge=45, le=120)

    # ── Session clustering ──
    sessions_per_day_min: int = Field(default=2, ge=1, le=4)
    sessions_per_day_max: int = Field(default=4, ge=2, le=6)

    # ── Schedule rules ──
    weekdays_only: bool = True
    timezone: str = "Asia/Karachi"

    # ── Targeting ──
    target_refresh_interval_days: int = Field(default=7, ge=1, le=30)
    target_profiles_per_persona: int = Field(default=150, ge=20, le=500)

    # ── Evidence threshold for research-grounded posts ──
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
    tone_of_voice: str = ""
    brand: BrandContext | None = None
    positioning: str = ""

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
    ticket_price: str = ""

    # Canonical campaign & intake fields
    campaign_type: str = ""
    campaign_name: str = ""
    objective: str = ""
    value_proposition: str = ""
    cta_url: str = ""

    # Explicit contextual facts
    campaign_category: str = ""
    outcome_value_proposition: str = ""
    product_facts: str = ""


class LinkedInPost(BaseModel):
    """Generated LinkedIn post ready for preview & scheduling."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    slot_id: str
    scheduled_at: datetime
    timezone: str = "UTC"
    schedule_reason: str = ""
    schedule_source: str = ""
    schedule_confidence: str = "medium"
    linkedin_account_id: str | None = None
    campaign_asset_id: UUID | None = None
    media_url: str | None = None
    media_type: str | None = None
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


# ── Targeting Models (DB-backed) ─────────────────────────────────────────────


class TargetPersona(BaseModel):
    """A target audience persona stored in ``linkedin_target_personas`` table."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID | None = None
    company_profile_id: UUID | None = None
    label: str  # e.g. "AI Founders"
    search_keywords: str  # e.g. "AI startup founder CEO"
    max_profiles: int = Field(default=150, ge=10, le=500)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResolvedTarget(BaseModel):
    """A specific LinkedIn profile resolved from a persona search."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    account_id: str
    persona_label: str
    profile_id: str  # Unipile/LinkedIn profile identifier
    display_name: str = ""
    headline: str = ""
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TargetPost(BaseModel):
    """A specific post from a resolved target, ready for engagement."""

    model_config = ConfigDict(frozen=True)

    post_id: str
    author_profile_id: str
    author_name: str
    content: str  # Full post text — this is ALL the LLM sees
    posted_at: datetime
    persona_label: str


# ── Review Queue Model ───────────────────────────────────────────────────────


class GeneratedComment(BaseModel):
    """AI-generated comment awaiting human review before publishing."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID | None = None
    company_profile_id: UUID | None = None
    linkedin_account_id: UUID | None = None
    action_log_id: UUID | None = None
    target_post_id: str
    target_post_snippet: str = ""  # First 200 chars for review context
    target_author_name: str = ""
    persona_label: str = ""
    generated_text: str
    status: ReviewStatus = ReviewStatus.PENDING_REVIEW
    reject_reason: str = ""
    unipile_id: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reviewed_at: datetime | None = None
    published_at: datetime | None = None


# ── Engagement Settings & Log Models ─────────────────────────────────────────


class EngagementSettings(BaseModel):
    """Brand-scoped engagement automation settings."""

    model_config = ConfigDict(frozen=False)

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    company_profile_id: UUID
    linkedin_account_id: UUID | None = None
    engagement_enabled: bool = False
    auto_like_enabled: bool = False
    auto_comment_generation_enabled: bool = False
    auto_connect_enabled: bool = False
    likes_per_day: int = Field(default=15, ge=0, le=100)
    comments_per_day: int = Field(default=5, ge=0, le=50)
    invites_per_day: int = Field(default=10, ge=0, le=40)
    connection_note_template: str = ""
    timezone: str = "UTC"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EngagementActionType(StrEnum):
    LIKE = "like"
    COMMENT = "comment"
    CONNECTION_REQUEST = "connection_request"


class EngagementLogStatus(StrEnum):
    CLAIMED = "claimed"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class EngagementLogEntry(BaseModel):
    """Authoritative durable event log & idempotency anchor."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    company_profile_id: UUID
    linkedin_account_id: UUID
    action_type: EngagementActionType
    target_post_id: str | None = None
    target_profile_id: str | None = None
    review_queue_id: UUID | None = None
    comment_text: str | None = None
    status: EngagementLogStatus = EngagementLogStatus.CLAIMED
    provider_result_id: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


# ── Warm-Up State ────────────────────────────────────────────────────────────


class WarmupState(BaseModel):
    """Persisted warm-up state for a LinkedIn account."""

    model_config = ConfigDict(frozen=False)  # Mutable — updated during ramp-up

    id: UUID = Field(default_factory=uuid4)
    linkedin_account_id: UUID | str
    activation_date: _dt.date = Field(default_factory=_dt.date.today)
    days_active: int = 0
    current_daily_invite_limit: int = 10
    current_daily_engage_limit: int = 15
    phase: WarmupPhase = WarmupPhase.RAMP_UP
    last_limit_increase_date: _dt.date | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ── Scheduling Dataclasses ───────────────────────────────────────────────────


@dataclass(frozen=True)
class SessionWindow:
    """One burst of activity within a daily schedule."""

    start: _dt.time
    end: _dt.time
    max_actions: int
    action_types: tuple[str, ...]  # e.g. ("like", "comment", "invite")


@dataclass(frozen=True)
class DailySchedule:
    """Immutable plan for one day's activity — generated fresh each morning."""

    date: _dt.date
    work_start: _dt.time
    work_end: _dt.time
    lunch_start: _dt.time
    lunch_duration_minutes: int
    sessions: tuple[SessionWindow, ...]


@dataclass
class SessionResult:
    """Outcome of executing a single session burst."""

    status: str = "completed"  # completed, aborted, error
    reason: str = ""
    actions_attempted: int = 0
    actions_succeeded: int = 0
    actions_failed: int = 0
    details: dict[str, Any] = field(default_factory=dict)
