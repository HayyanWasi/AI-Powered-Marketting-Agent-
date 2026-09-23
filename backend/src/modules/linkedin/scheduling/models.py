"""Canonical LinkedIn schedule models."""

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScheduleSlot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    slot_id: UUID = Field(default_factory=uuid4)
    scheduled_at_utc: datetime
    local_date: date
    local_time: time
    timezone: str
    platform: Literal["linkedin"] = "linkedin"
    schedule_reason: str
    schedule_source: str = "linkedin-benchmarks-v1"
    schedule_confidence: Literal["low", "medium", "high"] = "medium"

    @model_validator(mode="after")
    def validate_utc(self):
        if self.scheduled_at_utc.tzinfo is None:
            raise ValueError("scheduled_at_utc must be timezone-aware")
        return self


class SchedulePlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    platform: Literal["linkedin"] = "linkedin"
    campaign_start: date
    campaign_end: date
    primary_timezone: str
    timezone_policy: str = "campaign_timezone"
    timezone_source: str = "campaign_timezone"
    recommended_cadence: str
    cadence_reason: str
    density_score: float = Field(default=0.0, ge=0.0, le=1.0)
    target_post_count: int = Field(default=0, ge=0)
    density_factors: tuple[str, ...] = ()
    confidence: Literal["low", "medium", "high"] = "medium"
    schedule_source: str = "linkedin-benchmarks-v1"
    algorithm_version: str = "schedule-v1"
    slots: tuple[ScheduleSlot, ...]

    @model_validator(mode="after")
    def validate_slots(self):
        ids = [slot.slot_id for slot in self.slots]
        dates = [slot.local_date for slot in self.slots]
        if len(ids) != len(set(ids)) or len(dates) != len(set(dates)):
            raise ValueError("Schedule slots must have unique IDs and dates")
        if any(not self.campaign_start <= day <= self.campaign_end for day in dates):
            raise ValueError("Schedule slot is outside campaign boundaries")
        return self
