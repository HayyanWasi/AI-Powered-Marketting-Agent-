"""Role-specific brief slices + delta-only chief synthesis.

Verifies the compaction preserves every mandatory role fact, keeps BrandContext
guardrails and research evidence, sends the schedule by ordinal only, and that
the chief can never silently drop or recreate specialist sections.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time

import pytest

from src.models.brand_context import BrandContext
from src.modules.linkedin.scheduling.models import SchedulePlan, ScheduleSlot
from src.modules.linkedin.scheduling.slot_validation import (
    ScheduleSlotMismatchError,
    normalize_calendar_slots,
)
from src.modules.planning.agents import chief_strategist as cs
from src.modules.planning.agents import panel
from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import ChiefReconciliation

panel.register_planning_templates()


def _brand() -> BrandContext:
    return BrandContext(
        company_profile_id="00000000-0000-0000-0000-000000000001",
        company_name="Seemlessco Rentals", industry="Property rental",
        description="A rental marketplace.", target_audience="renters",
        brand_tone="warm, trustworthy", guidelines="Emphasise trust.",
        negative_guardrails=["no fake urgency", "no discriminatory language"],
    )


def _schedule(n: int = 3) -> SchedulePlan:
    slots = tuple(
        ScheduleSlot(scheduled_at_utc=datetime(2026, 9, 21 + i, 7, tzinfo=UTC),
                     local_date=date(2026, 9, 21 + i), local_time=time(12),
                     timezone="Asia/Karachi", schedule_reason=f"slot {i}")
        for i in range(n)
    )
    return SchedulePlan(campaign_start=date(2026, 9, 21), campaign_end=date(2026, 9, 24),
                        primary_timezone="Asia/Karachi", recommended_cadence=f"{n} posts",
                        cadence_reason="x", slots=slots)


def _brief() -> PlanBrief:
    return PlanBrief(
        user_goal="Promote September Special", brand=_brand(),
        company_name="Seemlessco Rentals", campaign_type="general_promotion",
        campaign_name="September Special", objective="Drive rental bookings",
        value_proposition="20% off quality rentals", target_audience="renters",
        schedule_plan=_schedule(3), platforms=("LinkedIn",),
    )


# ── A. every specialist receives its mandatory role facts ──
def test_mandatory_facts_reach_each_specialist():
    v = _brief().to_template_vars()
    for name in ("plan_audience_research", "plan_positioning", "plan_channel",
                 "plan_measurement", "plan_competitive"):
        p = panel.render_template(name, v)
        assert "September Special" in p          # campaign name
        assert "general_promotion" in p          # campaign type
        assert "Drive rental bookings" in p      # objective
        assert "20% off quality rentals" in p    # value proposition
        assert "Seemlessco Rentals" in p         # brand


# ── B. BrandContext guardrails survive compaction ──
def test_guardrails_survive_in_messaging_specialists():
    v = _brief().to_template_vars()
    for name in ("plan_audience_research", "plan_positioning", "plan_channel"):
        p = panel.render_template(name, v)
        assert "no fake urgency" in p
    # chief gets the compact guardrails line
    assert "no fake urgency" in v["brand_guardrails"]


# ── C. competitive still receives research evidence ──
def test_competitive_receives_research():
    v = _brief().to_template_vars("WEB RESEARCH EVIDENCE:\n- Rival Co (http://x)\n  cheap rentals")
    p = panel.render_template("plan_competitive", v)
    assert "Rival Co" in p
    assert "WEB RESEARCH EVIDENCE" in p
    # and specialists that must NOT get research don't
    for name in ("plan_audience_research", "plan_positioning", "plan_measurement"):
        assert "Rival Co" not in panel.render_template(name, v)


# ── D. channel receives every slot by ordinal, no UUID/UTC ──
def test_channel_schedule_is_ordinal_only():
    brief = _brief()
    v = brief.to_template_vars()
    p = panel.render_template("plan_channel", v)
    assert "1. 2026-09-21" in p
    assert "2. 2026-09-22" in p
    assert "3. 2026-09-23" in p
    for slot in brief.schedule_plan.slots:
        assert str(slot.slot_id) not in p            # no raw UUID
    assert "utc=" not in p  # no UTC timestamp
    assert "2026-09-21T" not in p
    # schedule is NOT sent to non-channel specialists
    assert "FIXED LINKEDIN SCHEDULE" not in panel.render_template("plan_measurement", v)


# ── E. channel planner cannot change slot count/time/identity ──
def test_slot_mutation_still_rejected():
    from src.modules.planning.models.campaign_plan import CalendarSlot
    schedule = _schedule(2)
    mutated = (
        CalendarSlot(slot_id=str(schedule.slots[0].slot_id),
                     scheduled_at_utc=datetime(2099, 1, 1, tzinfo=UTC)),
        CalendarSlot(slot_id=str(schedule.slots[1].slot_id)),
    )
    with pytest.raises(ScheduleSlotMismatchError):
        normalize_calendar_slots(mutated, schedule)


# ── F. all 5 specialists remain required ──
def test_five_specialists():
    assert set(panel.SPECIALISTS) == {
        "audience_research", "positioning", "competitive", "channel_plan", "measurement"}


def _panel() -> dict:
    return {
        "audience_research": {"objective": "grow", "personas": [{"name": "A"}], "smart_goals": []},
        "positioning": {"positioning_statement": "p", "unique_selling_proposition": "usp",
                        "tone_of_voice": "warm", "messaging_pillars": ["x"], "objection_handling": []},
        "channel_plan": {"platforms": [], "phases": [],
                         "calendar_slots": [{"slot_id": "uuid-1", "theme": "t"}], "overall_cadence": "s"},
        "measurement": {"kpis": [{"name": "k"}], "definition_of_success": "win"},
        "competitive": {"landscape": [{"name": "C"}], "differentiation_angle": "angle",
                        "whitespace_opportunities": ["w"]},
    }


# ── G. chief reconciliation cannot remove specialist sections ──
def test_chief_cannot_drop_sections():
    base = cs.assemble(_panel(), title="T", executive_summary="E")
    # An empty reconciliation must not erase anything.
    empty = ChiefReconciliation.model_validate({"title": "", "executive_summary": ""})
    out = cs._apply_reconciliation(base, empty)
    assert out.core_strategy.personas
    assert out.core_strategy.unique_selling_proposition == "usp"
    assert out.channel_plan.calendar_slots
    assert out.measurement.kpis
    assert out.competitive.landscape
    assert out.competitive.differentiation_angle == "angle"


# ── H. deterministic assembly produces a complete valid plan ──
def test_deterministic_assembly_complete():
    base = cs.assemble(_panel(), title="T", executive_summary="E")
    recon = ChiefReconciliation.model_validate(
        {"title": "New", "executive_summary": "Sum",
         "adjustments": {"unique_selling_proposition": "sharper usp"}})
    out = cs._apply_reconciliation(base, recon)
    assert out.title == "New"
    assert out.executive_summary == "Sum"
    assert out.core_strategy.unique_selling_proposition == "sharper usp"  # allowlisted delta applied
    assert out.core_strategy.tone_of_voice == "warm"                     # untouched
    assert [s.slot_id for s in out.channel_plan.calendar_slots] == ["uuid-1"]
