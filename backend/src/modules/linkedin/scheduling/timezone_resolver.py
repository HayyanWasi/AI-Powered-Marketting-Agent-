"""Deterministic scheduling timezone resolution."""

from __future__ import annotations

from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.models.audience import AudienceProfile


@dataclass(frozen=True)
class ResolvedTimezone:
    name: str
    source: str
    confidence: str


def _valid_timezone(value: str, *, explicit: bool) -> str | None:
    name = value.strip()
    if not name:
        return None
    try:
        return ZoneInfo(name).key
    except (ZoneInfoNotFoundError, ValueError) as exc:
        if explicit:
            raise ValueError(f"Invalid scheduling timezone: {name}") from exc
        return None


def resolve_scheduling_timezone(
    *,
    explicit_target_timezone: str = "",
    audience: AudienceProfile | None = None,
    campaign_timezone: str = "",
    creator_timezone: str = "",
) -> ResolvedTimezone:
    """Resolve a timezone without guessing among multiple audience regions."""
    # Validate every supplied explicit value even if a stronger source wins.
    target = _valid_timezone(explicit_target_timezone, explicit=True)
    campaign = _valid_timezone(campaign_timezone, explicit=True)
    creator = _valid_timezone(creator_timezone, explicit=True)
    if target:
        return ResolvedTimezone(target, "explicit_campaign_target", "high")

    audience_timezones = tuple(
        dict.fromkeys(
            timezone
            for raw in (audience.timezones if audience else ())
            if (timezone := _valid_timezone(raw, explicit=False))
        )
    )
    if len(audience_timezones) == 1:
        confidence = audience.confidence if audience else "medium"
        return ResolvedTimezone(audience_timezones[0], "audience_profile", confidence)

    if campaign:
        source = "campaign_timezone"
        confidence = "low" if len(audience_timezones) > 1 else "medium"
        return ResolvedTimezone(campaign, source, confidence)

    if creator:
        confidence = "low" if len(audience_timezones) > 1 else "medium"
        return ResolvedTimezone(creator, "creator_timezone", confidence)

    return ResolvedTimezone("UTC", "utc_fallback", "low")
