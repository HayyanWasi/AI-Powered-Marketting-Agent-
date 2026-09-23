from datetime import UTC, date, datetime, time

import pytest

from src.models.audience import AudienceProfile
from src.modules.linkedin.scheduling.models import SchedulePlan, ScheduleSlot
from src.modules.linkedin.scheduling.schedule_optimizer import ScheduleOptimizer
from src.modules.linkedin.scheduling.slot_validation import (
    ScheduleSlotMismatchError,
    normalize_calendar_slots,
)
from src.modules.linkedin.scheduling.timezone_resolver import resolve_scheduling_timezone
from src.modules.planning.models.campaign_plan import CalendarSlot


def test_timezone_precedence_and_sources():
    audience = AudienceProfile(
        summary="Primary UAE market", timezones=("Asia/Dubai",), confidence="high"
    )
    explicit = resolve_scheduling_timezone(
        explicit_target_timezone="Europe/London",
        audience=audience,
        campaign_timezone="Asia/Karachi",
        creator_timezone="America/New_York",
    )
    assert (explicit.name, explicit.source) == ("Europe/London", "explicit_campaign_target")

    audience_result = resolve_scheduling_timezone(
        audience=audience,
        campaign_timezone="Asia/Karachi",
        creator_timezone="America/New_York",
    )
    assert (audience_result.name, audience_result.source) == ("Asia/Dubai", "audience_profile")

    campaign = resolve_scheduling_timezone(
        campaign_timezone="Asia/Karachi", creator_timezone="America/New_York"
    )
    assert (campaign.name, campaign.source) == ("Asia/Karachi", "campaign_timezone")

    creator = resolve_scheduling_timezone(creator_timezone="America/New_York")
    assert (creator.name, creator.source) == ("America/New_York", "creator_timezone")

    utc = resolve_scheduling_timezone()
    assert (utc.name, utc.source, utc.confidence) == ("UTC", "utc_fallback", "low")


def test_multiple_audience_timezones_do_not_select_first():
    result = resolve_scheduling_timezone(
        audience=AudienceProfile(
            summary="Global audience",
            timezones=("Asia/Dubai", "Europe/London"),
            confidence="high",
        ),
        campaign_timezone="Asia/Karachi",
    )
    assert result.name == "Asia/Karachi"
    assert result.source == "campaign_timezone"
    assert result.confidence == "low"

    plan = ScheduleOptimizer.build(
        campaign_start=date(2026, 9, 21),
        campaign_end=date(2026, 9, 27),
        timezone_name=result.name,
        timezone_source=result.source,
        timezone_confidence=result.confidence,
        audience=AudienceProfile(
            summary="Global audience",
            timezones=("Asia/Dubai", "Europe/London"),
            confidence="high",
        ),
        now=datetime(2026, 9, 21, tzinfo=UTC),
    )
    assert plan.timezone_source == "campaign_timezone"
    assert plan.confidence == "low"


@pytest.mark.parametrize("field", ["explicit_target_timezone", "campaign_timezone", "creator_timezone"])
def test_invalid_explicit_timezone_fails_truthfully(field):
    with pytest.raises(ValueError, match="Invalid scheduling timezone: Not/A_Zone"):
        resolve_scheduling_timezone(**{field: "Not/A_Zone"})


def _schedule() -> SchedulePlan:
    slots = (
        ScheduleSlot(
            slot_id="00000000-0000-0000-0000-000000000001",
            scheduled_at_utc=datetime(2026, 9, 21, 7, tzinfo=UTC),
            local_date=date(2026, 9, 21),
            local_time=time(12),
            timezone="Asia/Karachi",
            schedule_reason="first",
        ),
        ScheduleSlot(
            slot_id="00000000-0000-0000-0000-000000000002",
            scheduled_at_utc=datetime(2026, 9, 23, 13, tzinfo=UTC),
            local_date=date(2026, 9, 23),
            local_time=time(18),
            timezone="Asia/Karachi",
            schedule_reason="second",
        ),
    )
    return SchedulePlan(
        campaign_start=date(2026, 9, 21),
        campaign_end=date(2026, 9, 27),
        primary_timezone="Asia/Karachi",
        recommended_cadence="2 posts",
        cadence_reason="test",
        slots=slots,
    )


def _calendars(schedule: SchedulePlan) -> tuple[CalendarSlot, ...]:
    return tuple(
        CalendarSlot(
            slot_id=str(slot.slot_id),
            date=slot.local_date.isoformat(),
            platform="LinkedIn",
        )
        for slot in schedule.slots
    )


def test_reordered_slots_are_accepted_and_normalized_chronologically():
    schedule = _schedule()
    normalized = normalize_calendar_slots(tuple(reversed(_calendars(schedule))), schedule)
    assert [slot.slot_id for slot in normalized] == [str(slot.slot_id) for slot in schedule.slots]
    assert [slot.scheduled_at_utc for slot in normalized] == [
        slot.scheduled_at_utc for slot in schedule.slots
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        {"scheduled_at_utc": datetime(2026, 9, 21, 8, tzinfo=UTC)},
        {"timezone": "UTC"},
        {"local_time": time(13)},
        {"date": "2026-09-22"},
        {"platform": "Instagram"},
        {"slot_id": "00000000-0000-0000-0000-000000000099"},
    ],
)
def test_slot_mutations_are_rejected(mutation):
    schedule = _schedule()
    calendar = list(_calendars(schedule))
    calendar[0] = calendar[0].model_copy(update=mutation)
    with pytest.raises(ScheduleSlotMismatchError):
        normalize_calendar_slots(tuple(calendar), schedule)


def test_added_and_removed_slots_are_rejected():
    schedule = _schedule()
    calendar = _calendars(schedule)
    with pytest.raises(ScheduleSlotMismatchError):
        normalize_calendar_slots(calendar[:-1], schedule)
    extra = CalendarSlot(
        slot_id="00000000-0000-0000-0000-000000000099",
        date="2026-09-25",
        platform="LinkedIn",
    )
    with pytest.raises(ScheduleSlotMismatchError):
        normalize_calendar_slots((*calendar, extra), schedule)
