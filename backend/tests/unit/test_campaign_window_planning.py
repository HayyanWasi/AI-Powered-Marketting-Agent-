"""Campaign validity window — planning integration (no planning redesign).

Proves the existing PlanBrief path carries the corrected campaign.schedule bounds
into the SchedulePlan, that every generated slot falls inside the requested
window, and that the LinkedIn schedule boundary consumes those exact dates
without modifying them.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import uuid4

import pytest

from src.models.brand_context import BrandContext
from src.models.campaign import Campaign, Schedule
from src.modules.linkedin.scheduling.models import ScheduleSlot
from src.modules.linkedin.scheduling.schedule_optimizer import ScheduleOptimizer
from src.modules.linkedin.scheduling.slot_validation import (
    ScheduleSlotMismatchError,
    normalize_calendar_slots,
)
from src.modules.planning.models.campaign_plan import CalendarSlot
from src.services.campaign_context_service import CampaignInputs

WINDOW_START = date(2026, 9, 20)
WINDOW_END = date(2026, 10, 1)


def _brand() -> BrandContext:
    return BrandContext(
        company_profile_id=uuid4(),
        company_name="Window Brand",
        brand_tone="Direct",
        negative_guardrails=("No buzzwords",),
        profile_updated_at="2026-09-17T10:00:00+00:00",
    )


def test_8_to_brief_carries_schedule_window() -> None:
    brand = _brand()
    campaign = Campaign(
        id=uuid4(),
        name="Window Campaign",
        company_profile_id=brand.company_profile_id,
        platforms=["linkedin"],
        schedule=Schedule(
            start_date=datetime(2026, 9, 20, tzinfo=UTC),
            end_date=datetime(2026, 10, 1, tzinfo=UTC),
            timezone="Asia/Karachi",
            recurrence_rule="FREQ=WEEKLY",
        ),
    )
    brief = CampaignInputs(campaign, brand, {"campaign_type": "general_promotion"}).to_brief()
    assert brief.campaign_start == "2026-09-20"
    assert brief.campaign_end == "2026-10-01"
    assert brief.campaign_timezone == "Asia/Karachi"


def test_9_schedule_plan_slots_within_window() -> None:
    plan = ScheduleOptimizer.build(
        campaign_start=WINDOW_START,
        campaign_end=WINDOW_END,
        timezone_name="Asia/Karachi",
        campaign_type="general_promotion",
        objective="Drive signups",
        event_date="",
        now=datetime(2026, 9, 19, tzinfo=UTC),  # deterministic "today"
    )
    assert plan.slots, "scheduler must produce at least one slot"
    dates = [slot.local_date for slot in plan.slots]
    # Every generated slot is inside the requested window; nothing after 1 Oct.
    assert all(WINDOW_START <= d <= WINDOW_END for d in dates), sorted(dates)
    assert max(dates) <= WINDOW_END
    # Post count remains owned by the scheduler (not asserted to any fixed number).


def test_10_linkedin_consumes_schedule_dates_unchanged() -> None:
    """normalize_calendar_slots binds content slots to the canonical schedule.

    LinkedIn never invents dates: a content slot must match the SchedulePlan slot,
    and its date is restored from the canonical schedule. A content slot that
    tries to change the date is rejected — proving dates flow one way, from the
    persisted SchedulePlan into LinkedIn.
    """
    plan = ScheduleOptimizer.build(
        campaign_start=WINDOW_START,
        campaign_end=WINDOW_END,
        timezone_name="Asia/Karachi",
        campaign_type="general_promotion",
        now=datetime(2026, 9, 19, tzinfo=UTC),
    )
    first = plan.slots[0]
    # A faithful content slot mirroring the canonical schedule normalizes cleanly
    # and keeps the schedule's date.
    good = CalendarSlot(
        slot_id=str(first.slot_id),
        date=first.local_date.isoformat(),
        platform="LinkedIn",
        theme="Launch",
        cta="Register",
    )
    single = ScheduleSlot(
        slot_id=first.slot_id,
        scheduled_at_utc=first.scheduled_at_utc,
        local_date=first.local_date,
        local_time=first.local_time,
        timezone=first.timezone,
        schedule_reason=first.schedule_reason,
    )
    single_plan = plan.model_copy(update={"slots": (single,)})
    normalized = normalize_calendar_slots((good,), single_plan)
    assert normalized[0].date == first.local_date.isoformat()

    # A content slot that tries to move the date outside/away is rejected.
    tampered = good.model_copy(update={"date": "2026-10-15"})
    with pytest.raises(ScheduleSlotMismatchError):
        normalize_calendar_slots((tampered,), single_plan)
