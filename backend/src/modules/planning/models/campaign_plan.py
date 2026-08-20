"""Campaign plan — the professional marketing plan a marketer reviews and refines.

The plan is the strategic backbone: it is drafted by a panel of specialist
agents, refined section-by-section through conversation, and must be approved
before any content or image generation runs.

Pydantic (rather than the frozen dataclasses in ``src/agents/context.py``) so
that the plan round-trips to JSONB, can pin an LLM's output shape via
``model_json_schema()``, and supports section-level patching via
``model_copy(update=...)``.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# The four top-level sections. These are the unit of refinement: a critique is
# routed to one or more of these names, and only those are regenerated.
SECTION_NAMES: tuple[str, ...] = (
    "core_strategy",
    "channel_plan",
    "measurement",
    "competitive",
)


def _coerce_tuple_str(v: Any) -> tuple[str, ...]:
    if isinstance(v, str):
        return tuple(s.strip() for s in v.split(",") if s.strip())
    if isinstance(v, (list, tuple)):
        return tuple(str(x) for x in v if x)
    return ()


def _coerce_tuple_dict(v: Any) -> tuple[Any, ...]:
    if isinstance(v, dict):
        return (v,)
    if isinstance(v, (list, tuple)):
        return tuple(x for x in v if x)
    return ()


class PlanStatus(str, Enum):
    """Lifecycle of a campaign plan."""

    DRAFTING = "Drafting"
    DRAFT = "Draft"
    REFINING = "Refining"
    APPROVED = "Approved"
    SUPERSEDED = "Superseded"


class CampaignPhase(str, Enum):
    """Phases a campaign moves through over its lifetime."""

    TEASER = "teaser"
    LAUNCH = "launch"
    SUSTAIN = "sustain"
    LAST_CALL = "last_call"


class FunnelStage(str, Enum):
    """Marketing funnel stages used to organise KPIs."""

    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    CONVERSION = "conversion"
    RETENTION = "retention"


class _Section(BaseModel):
    """Base for plan sections — frozen, and tolerant of extra LLM keys."""

    model_config = ConfigDict(frozen=True, extra="ignore")


# ── Core strategy ────────────────────────────────────────────────────────


class SmartGoal(_Section):
    """A single SMART goal."""

    goal: str = ""
    metric: str = ""
    target: str | int = ""
    deadline: str = ""


class Persona(_Section):
    """An audience segment rendered as an actionable persona."""

    name: str = ""
    description: str = ""
    demographics: str = ""
    motivations: tuple[str, ...] = ()
    pain_points: tuple[str, ...] = ()
    where_they_are: tuple[str, ...] = ()

    @field_validator("motivations", "pain_points", "where_they_are", mode="before")
    @classmethod
    def coerce_strings(cls, v: Any) -> tuple[str, ...]:
        return _coerce_tuple_str(v)


class Objection(_Section):
    """An anticipated objection and how the campaign answers it."""

    objection: str = ""
    response: str = ""


class CoreStrategy(_Section):
    """Objective, audience, positioning and messaging — the strategic spine."""

    objective: str = ""
    smart_goals: tuple[SmartGoal, ...] = ()
    personas: tuple[Persona, ...] = ()
    positioning_statement: str = ""
    unique_selling_proposition: str = ""
    messaging_pillars: tuple[str, ...] = ()
    tone_of_voice: str = ""
    objection_handling: tuple[Objection, ...] = ()

    @field_validator("messaging_pillars", mode="before")
    @classmethod
    def coerce_pillars(cls, v: Any) -> tuple[str, ...]:
        return _coerce_tuple_str(v)

    @field_validator("smart_goals", "personas", "objection_handling", mode="before")
    @classmethod
    def coerce_submodels(cls, v: Any) -> tuple[Any, ...]:
        return _coerce_tuple_dict(v)


# ── Channel plan & calendar ──────────────────────────────────────────────


class PlatformStrategy(_Section):
    """How the campaign behaves on one specific platform."""

    platform: str = ""
    rationale: str = ""
    content_formats: tuple[str, ...] = ()
    posting_cadence: str = ""
    tone_adjustment: str = ""
    hashtag_strategy: str = ""

    @field_validator("content_formats", mode="before")
    @classmethod
    def coerce_formats(cls, v: Any) -> tuple[str, ...]:
        return _coerce_tuple_str(v)


class PhasePlan(_Section):
    """Goal and messaging emphasis for one campaign phase."""

    phase: CampaignPhase
    duration: str = ""
    objective: str = ""
    key_message: str = ""
    primary_cta: str = ""

    @model_validator(mode="before")
    @classmethod
    def _remap_phase_keys(cls, data: Any) -> Any:
        if isinstance(data, dict) and "phase" not in data:
            for k in ("phase_name", "name", "title", "stage"):
                if k in data:
                    d = dict(data)
                    d["phase"] = d.pop(k)
                    return d
        return data

    @field_validator("phase", mode="before")
    @classmethod
    def coerce_phase(cls, v: Any) -> Any:  # noqa: N805
        """Map any LLM-generated phase string to the nearest CampaignPhase."""
        if isinstance(v, CampaignPhase):
            return v
        s = str(v).lower().replace("-", "_").replace(" ", "_")
        _PHASE_ALIASES: dict[str, CampaignPhase] = {
            "teaser": CampaignPhase.TEASER,
            "pre_launch": CampaignPhase.TEASER,
            "awareness": CampaignPhase.TEASER,
            "launch": CampaignPhase.LAUNCH,
            "launch_day": CampaignPhase.LAUNCH,
            "single_post": CampaignPhase.LAUNCH,
            "announcement": CampaignPhase.LAUNCH,
            "sustain": CampaignPhase.SUSTAIN,
            "sustaining": CampaignPhase.SUSTAIN,
            "engagement": CampaignPhase.SUSTAIN,
            "ongoing": CampaignPhase.SUSTAIN,
            "maintenance": CampaignPhase.SUSTAIN,
            "last_call": CampaignPhase.LAST_CALL,
            "closing": CampaignPhase.LAST_CALL,
            "final": CampaignPhase.LAST_CALL,
            "post_event": CampaignPhase.LAST_CALL,
        }
        if s in _PHASE_ALIASES:
            return _PHASE_ALIASES[s]
        # Unknown value: default to LAUNCH and log a warning
        import logging
        logging.getLogger(__name__).warning(
            "Unknown CampaignPhase %r — defaulting to 'launch'", v
        )
        return CampaignPhase.LAUNCH


class CalendarSlot(_Section):
    """A single planned post. Consumed by the campaign planner agent."""

    slot_id: str = Field(default_factory=lambda: str(uuid4()))
    date: str = ""
    platform: str = ""
    phase: CampaignPhase = CampaignPhase.LAUNCH
    theme: str = ""
    format_type: str = ""
    messaging_pillar: str = ""
    cta: str = ""

    @field_validator("phase", mode="before")
    @classmethod
    def coerce_phase(cls, v: Any) -> Any:  # noqa: N805
        return PhasePlan.coerce_phase(v)


class ChannelPlan(_Section):
    """Per-platform strategy, phasing, and the dated content calendar."""

    platforms: tuple[PlatformStrategy, ...] = ()
    phases: tuple[PhasePlan, ...] = ()
    calendar_slots: tuple[CalendarSlot, ...] = ()
    overall_cadence: str = ""

    @field_validator("platforms", "phases", "calendar_slots", mode="before")
    @classmethod
    def coerce_submodels(cls, v: Any) -> tuple[Any, ...]:
        return _coerce_tuple_dict(v)


# ── Measurement ──────────────────────────────────────────────────────────


class Kpi(_Section):
    """A single tracked metric with its target."""

    name: str = ""
    funnel_stage: FunnelStage = FunnelStage.AWARENESS
    target: str = ""
    measurement_method: str = ""

    @field_validator("funnel_stage", mode="before")
    @classmethod
    def coerce_funnel_stage(cls, v: Any) -> Any:  # noqa: N805
        """Map any LLM-generated funnel stage to the nearest FunnelStage."""
        if isinstance(v, FunnelStage):
            return v
        s = str(v).lower().replace("-", "_").replace(" ", "_")
        _STAGE_ALIASES: dict[str, FunnelStage] = {
            "awareness": FunnelStage.AWARENESS,
            "reach": FunnelStage.AWARENESS,
            "top_of_funnel": FunnelStage.AWARENESS,
            "tofu": FunnelStage.AWARENESS,
            "consideration": FunnelStage.CONSIDERATION,
            "interest": FunnelStage.CONSIDERATION,
            "mofu": FunnelStage.CONSIDERATION,
            "engagement": FunnelStage.CONSIDERATION,
            "conversion": FunnelStage.CONVERSION,
            "registration": FunnelStage.CONVERSION,
            "bofu": FunnelStage.CONVERSION,
            "sign_up": FunnelStage.CONVERSION,
            "retention": FunnelStage.RETENTION,
            "loyalty": FunnelStage.RETENTION,
            "advocacy": FunnelStage.RETENTION,
        }
        if s in _STAGE_ALIASES:
            return _STAGE_ALIASES[s]
        import logging
        logging.getLogger(__name__).warning(
            "Unknown FunnelStage %r — defaulting to 'awareness'", v
        )
        return FunnelStage.AWARENESS


class Measurement(_Section):
    """What success looks like and how it is tracked."""

    kpis: tuple[Kpi, ...] = ()
    tracking_plan: str = ""
    reporting_cadence: str = ""
    definition_of_success: str = ""

    @field_validator("kpis", mode="before")
    @classmethod
    def coerce_submodels(cls, v: Any) -> tuple[Any, ...]:
        return _coerce_tuple_dict(v)


# ── Competitive ──────────────────────────────────────────────────────────


class Competitor(_Section):
    """A competitor or comparable campaign in the landscape."""

    name: str = ""
    positioning: str = ""
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    source_url: str = ""

    @field_validator("strengths", "weaknesses", mode="before")
    @classmethod
    def coerce_strings(cls, v: Any) -> tuple[str, ...]:
        return _coerce_tuple_str(v)


class Competitive(_Section):
    """Landscape scan and the resulting differentiation angle."""

    landscape: tuple[Competitor, ...] = ()
    differentiation_angle: str = ""
    whitespace_opportunities: tuple[str, ...] = ()

    @field_validator("whitespace_opportunities", mode="before")
    @classmethod
    def coerce_opportunities(cls, v: Any) -> tuple[str, ...]:
        return _coerce_tuple_str(v)

    @field_validator("landscape", mode="before")
    @classmethod
    def coerce_submodels(cls, v: Any) -> tuple[Any, ...]:
        return _coerce_tuple_dict(v)


# ── The plan ─────────────────────────────────────────────────────────────


class CampaignPlan(BaseModel):
    """A complete, reviewable marketing plan for one campaign."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    plan_id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID | None = None
    version: int = 1
    language: str = "en"
    status: PlanStatus = PlanStatus.DRAFT
    approved: bool = False

    title: str = ""
    executive_summary: str = ""

    core_strategy: CoreStrategy = Field(default_factory=CoreStrategy)
    channel_plan: ChannelPlan = Field(default_factory=ChannelPlan)
    measurement: Measurement = Field(default_factory=Measurement)
    competitive: Competitive = Field(default_factory=Competitive)

    generated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_document(self) -> dict[str, Any]:
        """Serialize to a JSONB-ready document."""
        return self.model_dump(mode="json")

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> CampaignPlan:
        """Rebuild a plan from its stored JSONB document."""
        return cls.model_validate(document)

    def patch_sections(self, sections: dict[str, Any]) -> CampaignPlan:
        """Return a new plan with the named sections replaced.

        Only keys in SECTION_NAMES are applied; anything else is ignored so a
        misrouted critique cannot corrupt plan metadata.
        """
        doc = self.to_document()
        for k, v in sections.items():
            if k in SECTION_NAMES:
                doc[k] = v
        return self.model_validate(doc)

    def to_strategy_data(self):
        """Project the plan onto the legacy StrategyData shape.

        Keeps the existing generation pipeline working while it reads the
        richer plan through ``GenerationContext.plan``.
        """
        from src.agents.context import StrategyData

        ctas = tuple(p.primary_cta for p in self.channel_plan.phases if p.primary_cta)
        return StrategyData(
            usp_hook=self.core_strategy.unique_selling_proposition,
            messaging_pillars=self.core_strategy.messaging_pillars,
            objection_handling=tuple(
                f"{o.objection} — {o.response}" for o in self.core_strategy.objection_handling
            ),
            cta_hierarchy=ctas,
            approved=self.approved,
        )


class PlanMessage(BaseModel):
    """One turn in the plan refinement conversation."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    plan_id: UUID
    role: str
    content: str
    language: str = "en"
    sections_targeted: tuple[str, ...] = ()
    resulting_version: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlanVersion(BaseModel):
    """An immutable snapshot of the plan at one revision."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    plan_id: UUID
    version: int
    document: dict[str, Any]
    parent_version: int | None = None
    change_summary: str = ""
    sections_changed: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=datetime.utcnow)
