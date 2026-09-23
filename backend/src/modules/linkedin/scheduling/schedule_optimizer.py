"""Deterministic, explainable LinkedIn schedule optimization."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from math import ceil
from zoneinfo import ZoneInfo

from src.models.audience import AudienceProfile
from src.modules.linkedin.scheduling.models import SchedulePlan, ScheduleSlot


@dataclass(frozen=True)
class _DensityDecision:
    score: float
    weekly_rate: float
    target_count: int
    factors: tuple[str, ...]


@dataclass(frozen=True)
class _Candidate:
    day: date
    local_time: time
    score: float
    factors: tuple[str, ...]


class ScheduleOptimizer:
    """Create exact slots from campaign density and audience-behaviour scores."""

    _CANDIDATE_WINDOWS = (
        time(6, 30),
        time(7, 30),
        time(8, 0),
        time(9, 0),
        time(10, 30),
        time(12, 30),
        time(13, 30),
        time(16, 30),
        time(18, 0),
        time(20, 0),
    )
    _BASE_TIME_SCORES = {
        time(6, 30): 0.24,
        time(7, 30): 0.36,
        time(8, 0): 0.44,
        time(9, 0): 0.50,
        time(10, 30): 0.58,
        time(12, 30): 0.60,
        time(13, 30): 0.46,
        time(16, 30): 0.56,
        time(18, 0): 0.48,
        time(20, 0): 0.28,
    }
    _BASE_DAY_SCORES = {0: 0.08, 1: 0.20, 2: 0.22, 3: 0.18, 4: 0.05, 5: -0.12, 6: -0.16}
    _TIME_BOUND_TYPES = {
        "app_launch",
        "product_launch",
        "service_launch",
        "physical_event",
        "webinar",
    }
    _MAX_TOTAL_POSTS = 24

    @classmethod
    def build(
        cls,
        *,
        campaign_start: date,
        campaign_end: date,
        timezone_name: str,
        timezone_source: str = "campaign_timezone",
        timezone_confidence: str | None = None,
        audience: AudienceProfile | None = None,
        campaign_type: str = "",
        objective: str = "",
        event_date: str = "",
        now: datetime | None = None,
    ) -> SchedulePlan:
        try:
            tz = ZoneInfo(timezone_name)
        except Exception as exc:
            raise ValueError(f"Invalid scheduling timezone: {timezone_name}") from exc
        timezone_name = getattr(tz, "key", "UTC")
        today = (now or datetime.now(UTC)).astimezone(tz).date()
        start = max(campaign_start, today)
        if campaign_end < start:
            raise ValueError("Campaign end date must not be before its effective start date")

        density = cls._density(
            start=start,
            end=campaign_end,
            campaign_type=campaign_type,
            objective=objective,
            event_date=event_date,
            today=today,
        )
        candidates = cls._candidates(
            start=start,
            end=campaign_end,
            audience=audience,
            objective=objective,
            event_date=event_date,
        )
        ranked = cls._select(candidates, density.target_count, start, campaign_end)
        confidence = timezone_confidence or (
            audience.confidence if audience and audience.is_usable() else "low"
        )
        slots = tuple(
            ScheduleSlot(
                local_date=item.day,
                local_time=item.local_time,
                timezone=timezone_name,
                scheduled_at_utc=datetime.combine(item.day, item.local_time, tzinfo=tz).astimezone(
                    UTC
                ),
                schedule_reason=(f"score={item.score:.3f}; " + "; ".join(item.factors)),
                schedule_source="explainable-linkedin-priors-v2",
                schedule_confidence=confidence,
            )
            for item in ranked
        )
        return SchedulePlan(
            campaign_start=start,
            campaign_end=campaign_end,
            primary_timezone=timezone_name,
            timezone_policy=timezone_source,
            timezone_source=timezone_source,
            recommended_cadence=(
                f"{len(slots)} posts across {(campaign_end - start).days + 1} days "
                f"(~{density.weekly_rate:.1f}/week)"
            ),
            cadence_reason="; ".join(density.factors),
            density_score=density.score,
            target_post_count=density.target_count,
            density_factors=density.factors,
            confidence=confidence,
            schedule_source="explainable-linkedin-priors-v2",
            algorithm_version="schedule-v2",
            slots=slots,
        )

    @classmethod
    def _density(
        cls,
        *,
        start: date,
        end: date,
        campaign_type: str,
        objective: str,
        event_date: str,
        today: date,
    ) -> _DensityDecision:
        duration_days = (end - start).days + 1
        score = 0.30
        factors = ["baseline sustainable density +0.30"]
        normalized_type = campaign_type.strip().lower()
        objective_text = objective.lower()

        if normalized_type in {"physical_event", "webinar"}:
            score += 0.22
            factors.append("attendance deadline campaign +0.22")
        elif normalized_type in {"app_launch", "product_launch", "service_launch"}:
            score += 0.18
            factors.append("launch campaign +0.18")

        if any(
            term in objective_text
            for term in (
                "register",
                "registration",
                "download",
                "lead",
                "sale",
                "purchase",
                "book",
                "booking",
                "apply",
                "application",
                "conversion",
            )
        ):
            score += 0.12
            factors.append("action/conversion objective +0.12")
        if any(
            term in objective_text for term in ("thought leadership", "authority", "expert insight")
        ):
            score -= 0.12
            factors.append("thought-leadership depth -0.12")
        elif any(
            term in objective_text
            for term in (
                "awareness",
                "educate",
                "education",
                "inform",
                "prevention",
            )
        ):
            score += 0.02
            factors.append("awareness/education objective +0.02")

        deadline = cls._parse_date(event_date)
        if deadline:
            days_until = (deadline - today).days
            if days_until <= 2:
                score += 0.28
                factors.append("deadline within 2 days +0.28")
            elif days_until <= 7:
                score += 0.20
                factors.append("deadline within 7 days +0.20")
            elif days_until <= 14:
                score += 0.12
                factors.append("deadline within 14 days +0.12")
            elif days_until <= 30:
                score += 0.05
                factors.append("deadline within 30 days +0.05")
            elif days_until > 45:
                score -= 0.04
                factors.append("deadline more than 45 days away -0.04")

        if duration_days <= 7:
            score += 0.12
            factors.append("short campaign window +0.12")
        elif duration_days <= 14:
            score += 0.06
            factors.append("compact campaign window +0.06")
        elif duration_days >= 45:
            score -= 0.07
            factors.append("long campaign sustainability -0.07")

        score = min(1.0, max(0.0, score))
        weekly_rate = 1.10 + (1.90 * score)
        raw_target = round((duration_days / 7.0) * weekly_rate)
        phase_floor = (
            3
            if (duration_days >= 3 and (normalized_type in cls._TIME_BOUND_TYPES or deadline))
            else 1
        )
        safe_max = min(
            duration_days,
            cls._MAX_TOTAL_POSTS,
            max(1, ceil(duration_days * 0.55)),
        )
        target = min(safe_max, max(phase_floor, raw_target, 1))
        factors.extend(
            (
                f"density score {score:.2f}",
                f"bounded target {target} within 1..{safe_max}",
            )
        )
        return _DensityDecision(score, weekly_rate, target, tuple(factors))

    @classmethod
    def _candidates(
        cls,
        *,
        start: date,
        end: date,
        audience: AudienceProfile | None,
        objective: str,
        event_date: str,
    ) -> tuple[_Candidate, ...]:
        candidates: list[_Candidate] = []
        cursor = start
        while cursor <= end:
            for window in cls._CANDIDATE_WINDOWS:
                score, factors = cls._candidate_score(
                    cursor, window, audience, objective, event_date
                )
                candidates.append(_Candidate(cursor, window, score, factors))
            cursor += timedelta(days=1)
        return tuple(candidates)

    @classmethod
    def _candidate_score(
        cls,
        day: date,
        local_time: time,
        audience: AudienceProfile | None,
        objective: str,
        event_date: str,
    ) -> tuple[float, tuple[str, ...]]:
        score = cls._BASE_TIME_SCORES[local_time] + cls._BASE_DAY_SCORES[day.weekday()]
        factors = [
            f"window prior {cls._BASE_TIME_SCORES[local_time]:+.2f}",
            f"weekday prior {cls._BASE_DAY_SCORES[day.weekday()]:+.2f}",
        ]
        profile_text = cls._audience_text(audience)
        weekend = day.weekday() >= 5

        if any(
            term in profile_text
            for term in (
                "shift",
                "handover",
                "healthcare",
                "hospital",
                "operations",
            )
        ):
            if local_time in {time(6, 30), time(7, 30), time(13, 30)}:
                score += 0.42
                factors.append("shift-change availability +0.42")
            if weekend:
                score += 0.08
                factors.append("shift audience weekend availability +0.08")
        elif any(
            term in profile_text
            for term in (
                "executive",
                "founder",
                "decision-maker",
                "decision maker",
                "b2b",
                "director",
                "c-suite",
                "ceo",
            )
        ):
            if local_time in {time(7, 30), time(8, 0), time(18, 0)}:
                score += 0.40
                factors.append("executive before/after-work window +0.40")
            score += -0.34 if weekend else 0.18
            factors.append(
                "executive weekday preference +0.18"
                if not weekend
                else "executive weekend penalty -0.34"
            )
        elif any(
            term in profile_text
            for term in (
                "consumer",
                "mobile",
                "community",
                "job seeker",
                "b2c",
                "after work",
            )
        ):
            if local_time in {time(12, 30), time(16, 30), time(18, 0), time(20, 0)}:
                score += 0.34
                factors.append("consumer break/evening window +0.34")
            if weekend:
                score += 0.38
                factors.append("consumer weekend availability +0.38")
        elif any(term in profile_text for term in ("developer", "software", "technology", "tech")):
            if local_time in {time(10, 30), time(16, 30)}:
                score += 0.30
                factors.append("technical work-break window +0.30")
            if not weekend:
                score += 0.12
                factors.append("technical weekday preference +0.12")

        objective_text = objective.lower()
        if any(
            term in objective_text for term in ("register", "download", "book", "apply", "sale")
        ):
            if local_time in {time(12, 30), time(16, 30), time(18, 0)}:
                score += 0.10
                factors.append("action objective response window +0.10")
        elif any(term in objective_text for term in ("awareness", "educate", "inform")):
            if local_time in {time(10, 30), time(12, 30), time(18, 0)}:
                score += 0.08
                factors.append("awareness dwell-time window +0.08")
            if weekend:
                score += 0.05
                factors.append("awareness weekend reach +0.05")
        elif (
            any(
                term in objective_text
                for term in ("thought leadership", "authority", "expert insight")
            )
            and local_time in {time(8, 0), time(10, 30)}
            and not weekend
        ):
            score += 0.16
            factors.append("thought-leadership weekday focus +0.16")

        deadline = cls._parse_date(event_date)
        if deadline:
            days_before = (deadline - day).days
            if days_before == 0:
                score += 0.30
                factors.append("deadline-day relevance +0.30")
            elif 1 <= days_before <= 3:
                score += 0.22
                factors.append("last-call phase +0.22")
            elif 4 <= days_before <= 7:
                score += 0.10
                factors.append("deadline approach +0.10")
            elif days_before < 0:
                score -= 0.50
                factors.append("after supplied event date -0.50")
        return score, tuple(factors)

    @classmethod
    def _select(
        cls,
        candidates: tuple[_Candidate, ...],
        target: int,
        start: date,
        end: date,
    ) -> tuple[_Candidate, ...]:
        if not candidates or target <= 0:
            return ()
        selected: list[_Candidate] = []
        used_dates: set[date] = set()
        span = max(0, (end - start).days)
        for index in range(target):
            anchor_offset = round(index * span / max(1, target - 1)) if target > 1 else span // 2
            anchor = start + timedelta(days=anchor_offset)
            best: _Candidate | None = None
            best_score = float("-inf")
            best_anchor_score = 0.0
            best_spacing_score = 0.0
            for item in candidates:
                if item.day in used_dates:
                    continue
                anchor_score = -0.075 * abs((item.day - anchor).days)
                spacing_score = cls._spacing_score(item.day, selected)
                total = item.score + anchor_score + spacing_score
                item_order = (
                    item.day.toordinal() * 1440 + item.local_time.hour * 60 + item.local_time.minute
                )
                best_order = (
                    best.day.toordinal() * 1440 + best.local_time.hour * 60 + best.local_time.minute
                    if best
                    else 0
                )
                if best is None or (total, -item_order) > (best_score, -best_order):
                    best = item
                    best_score = total
                    best_anchor_score = anchor_score
                    best_spacing_score = spacing_score
            if best is None:
                break
            selected.append(
                _Candidate(
                    best.day,
                    best.local_time,
                    best_score,
                    best.factors
                    + (
                        f"distribution anchor {anchor.isoformat()} {best_anchor_score:+.2f}",
                        f"spacing quality {best_spacing_score:+.2f}",
                    ),
                )
            )
            used_dates.add(best.day)
        return tuple(sorted(selected, key=lambda item: (item.day, item.local_time)))

    @staticmethod
    def _spacing_score(day: date, selected: list[_Candidate]) -> float:
        if not selected:
            return 0.0
        nearest = min(abs((day - item.day).days) for item in selected)
        if nearest <= 1:
            return -0.70
        if nearest == 2:
            return 0.10
        if nearest <= 4:
            return 0.24
        return 0.18

    @staticmethod
    def _parse_date(value: str) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None

    @staticmethod
    def _audience_text(audience: AudienceProfile | None) -> str:
        if not audience:
            return ""
        values = (
            audience.summary,
            *audience.occupation_groups,
            *audience.industries,
            *audience.seniority_levels,
            *audience.work_environments,
            *audience.schedule_patterns,
            *audience.attention_patterns,
        )
        return " ".join(values).lower()
