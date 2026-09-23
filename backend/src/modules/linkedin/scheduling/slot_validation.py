"""Validation for the immutable boundary between schedule and content calendars."""

from __future__ import annotations

from src.modules.linkedin.scheduling.models import SchedulePlan
from src.modules.planning.models.campaign_plan import CalendarSlot


class ScheduleSlotMismatchError(ValueError):
    """Raised when a planner changes the canonical schedule structure."""


def normalize_calendar_slots(
    calendar_slots: tuple[CalendarSlot, ...], schedule_plan: SchedulePlan
) -> tuple[CalendarSlot, ...]:
    """Validate slots by identity/content and restore canonical chronology."""
    expected = {str(slot.slot_id): slot for slot in schedule_plan.slots}
    returned: dict[str, CalendarSlot] = {}
    for item in calendar_slots:
        if item.slot_id in returned:
            raise ScheduleSlotMismatchError("Duplicate schedule slot ID.")
        returned[item.slot_id] = item

    if set(returned) != set(expected):
        raise ScheduleSlotMismatchError("Added, removed, or unknown schedule slot.")

    normalized: list[CalendarSlot] = []
    for canonical in schedule_plan.slots:
        item = returned[str(canonical.slot_id)]
        if item.date and item.date != canonical.local_date.isoformat():
            raise ScheduleSlotMismatchError("Schedule slot date changed.")
        if item.platform and item.platform.strip().lower() != canonical.platform:
            raise ScheduleSlotMismatchError("Schedule slot platform changed.")
        if item.scheduled_at_utc and item.scheduled_at_utc != canonical.scheduled_at_utc:
            raise ScheduleSlotMismatchError("Schedule slot timestamp changed.")
        if item.local_time and item.local_time != canonical.local_time:
            raise ScheduleSlotMismatchError("Schedule slot local time changed.")
        if item.timezone and item.timezone != canonical.timezone:
            raise ScheduleSlotMismatchError("Schedule slot timezone changed.")
        normalized.append(item.model_copy(update={
            "date": canonical.local_date.isoformat(),
            "platform": "LinkedIn",
            "scheduled_at_utc": canonical.scheduled_at_utc,
            "local_time": canonical.local_time,
            "timezone": canonical.timezone,
        }))
    return tuple(normalized)
