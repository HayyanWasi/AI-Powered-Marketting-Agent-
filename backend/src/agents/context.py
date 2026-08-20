"""Immutable GenerationContext — snapshot of all data for a workflow execution.

Rule: All workflow nodes MUST consume only this context.
No workflow node may re-read business data from persistent storage
during the same execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from src.modules.planning.models.campaign_plan import CampaignPlan


@dataclass(frozen=True)
class BrandData:
    """Snapshot of company brand information."""

    company_name: str = ""
    brand_guidelines: str = ""
    brand_tone: str = ""
    reference_image_urls: tuple[str, ...] = ()
    style_guide: str = ""


@dataclass(frozen=True)
class GuestData:
    """Snapshot of a guest/speaker profile."""

    full_name: str
    position: str = ""
    organization: str = ""
    biography: str = ""
    expertise: tuple[str, ...] = ()
    confidence: str = "LOW"


@dataclass(frozen=True)
class EventData:
    """Snapshot of event details."""

    event_name: str = ""
    event_date: str = ""
    venue: str = ""
    platforms: tuple[str, ...] = ()
    registration_link: str = ""
    ticket_price: str = "Free"
    category: str | None = None
    outcome_deliverable: str | None = None


@dataclass(frozen=True)
class StrategyData:
    """Output from Strategy Agent — populated during workflow."""

    usp_hook: str = ""
    messaging_pillars: tuple[str, ...] = ()
    objection_handling: tuple[str, ...] = ()
    cta_hierarchy: tuple[str, ...] = ()
    approved: bool = False


@dataclass(frozen=True)
class ContentSlot:
    """A single content slot in the calendar."""

    slot_id: str
    date: str
    platform: str
    phase: str
    theme: str
    format_type: str
    category: str | None = None


@dataclass(frozen=True)
class ContentDraft:
    """Generated content for a single slot."""

    slot_id: str
    variant_a: str = ""
    variant_b: str = ""
    variant_c: str = ""
    image_prompt: str = ""
    selected_variant: str = ""
    image_url: str = ""
    image_model: str = ""
    hook_score: int = 0
    readability_score: float = 0.0


@dataclass(frozen=True)
class ValidationResult:
    """Result of content validation."""

    passed: bool
    character_count: int = 0
    character_limit: int = 0
    violations: tuple[str, ...] = ()
    image_valid: bool = False


@dataclass(frozen=True)
class GenerationContext:
    """Immutable context for a single workflow execution.

    Created ONCE before any agent runs.
    All agents read from this context only.
    No agent reads from database during execution.
    """

    context_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Input data (populated by Context Builder)
    brand: BrandData = field(default_factory=BrandData)
    guests: tuple[GuestData, ...] = ()
    event: EventData = field(default_factory=EventData)

    # Free-text goal the marketer typed (e.g. "campaigns for an AI hackathon")
    user_goal: str = ""

    # Reference posts for style matching
    reference_posts: tuple[str, ...] = ()

    # Approved marketing plan (loaded by Context Builder before the graph runs).
    # This is the strategic source of truth; StrategyData below is a projection
    # of it kept for the existing pipeline nodes.
    plan: "CampaignPlan | None" = None

    # Strategy output (populated by Strategy Agent)
    strategy: StrategyData = field(default_factory=StrategyData)

    # Calendar slots (populated by Campaign Planner Agent)
    calendar: tuple[ContentSlot, ...] = ()

    # Content drafts (populated by Content Generation Agent)
    content_drafts: tuple[ContentDraft, ...] = ()

    # Validation results (populated by Validation Agent)
    validation_results: tuple[ValidationResult, ...] = ()

    # SEO data (populated before content generation)
    hashtags: tuple[str, ...] = ()
    trending_topics: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()

    # Control
    current_step: str = "init"
    errors: tuple[str, ...] = ()
    human_feedback: str = ""
