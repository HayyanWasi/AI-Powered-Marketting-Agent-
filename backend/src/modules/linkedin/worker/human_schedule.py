"""Human Schedule Builder.

Generates a randomized, naturally-varying daily schedule based on the
bounds defined in AutoPilotConfig.
"""

from __future__ import annotations

import logging
import random
from datetime import UTC, datetime, time, timedelta

from src.modules.linkedin.models import AutoPilotConfig, DailySchedule, SessionWindow, WarmupState

logger = logging.getLogger(__name__)


class HumanSchedule:
    """Builds varied daily schedules that mimic human behavior."""

    def plan_and_schedule_day(
        self,
        config: AutoPilotConfig,
        warmup_state: WarmupState,
        schedule_date: datetime | None = None,
    ) -> DailySchedule:
        """Create a randomized schedule for the day.

        Args:
            config: Bounds for schedule variation.
            warmup_state: Current daily limits from warm-up phase.
            schedule_date: The date to schedule for (defaults to today in UTC,
                though in practice should use the account's timezone).
        """
        if not schedule_date:
            schedule_date = datetime.now(UTC)

        current_date = schedule_date.date()

        # 1. Randomize workday boundaries
        work_start_hr = random.randint(config.work_start_earliest, config.work_start_latest)
        work_start_min = random.randint(0, 59)
        work_start = time(hour=work_start_hr, minute=work_start_min)

        work_end_hr = random.randint(config.work_end_earliest, config.work_end_latest)
        work_end_min = random.randint(0, 59)
        work_end = time(hour=work_end_hr, minute=work_end_min)

        # 2. Randomize lunch break
        lunch_start_hr = random.randint(config.lunch_start_earliest, config.lunch_start_latest)
        lunch_start_min = random.randint(0, 59)
        lunch_start = time(hour=lunch_start_hr, minute=lunch_start_min)

        lunch_dur = random.randint(
            config.lunch_duration_min_minutes, config.lunch_duration_max_minutes
        )

        # 3. Create Sessions
        num_sessions = random.randint(config.sessions_per_day_min, config.sessions_per_day_max)

        # Calculate available minutes (excluding lunch)
        lunch_start_dt = datetime.combine(current_date, lunch_start)
        lunch_end_dt = lunch_start_dt + timedelta(minutes=lunch_dur)

        work_start_dt = datetime.combine(current_date, work_start)
        work_end_dt = datetime.combine(current_date, work_end)

        # Very basic session distribution logic
        sessions: list[SessionWindow] = []

        # Distribute the daily limit across sessions
        total_actions = (
            warmup_state.current_daily_engage_limit + warmup_state.current_daily_invite_limit
        )
        if num_sessions > 0 and total_actions > 0:
            actions_per_session = max(1, total_actions // num_sessions)
            extra_actions = total_actions % num_sessions

            # Simple chronological distribution
            total_work_minutes = int((work_end_dt - work_start_dt).total_seconds() / 60) - lunch_dur
            if total_work_minutes < num_sessions * 30:
                logger.warning("Work day too short for requested sessions, adjusting...")
                num_sessions = max(1, total_work_minutes // 30)

            # Generate random session start times
            current_time = work_start_dt
            for i in range(num_sessions):
                # How many actions for this session?
                sess_actions = actions_per_session + (1 if i < extra_actions else 0)

                # Minimum session duration: say 2 mins per action + buffer
                sess_dur = sess_actions * 2 + 10

                # Avoid lunch
                if lunch_start_dt <= current_time < lunch_end_dt:
                    current_time = lunch_end_dt

                sess_end = current_time + timedelta(minutes=sess_dur)
                if sess_end > lunch_start_dt and current_time < lunch_start_dt:
                    # Snaps to before lunch if it overlaps
                    sess_end = lunch_start_dt

                if sess_end > work_end_dt:
                    sess_end = work_end_dt

                sessions.append(
                    SessionWindow(
                        start=current_time.time(),
                        end=sess_end.time(),
                        max_actions=sess_actions,
                        action_types=("like", "comment", "invite"),
                    )
                )

                # Advance current_time for next session
                gap_minutes = random.randint(30, 90)
                current_time = sess_end + timedelta(minutes=gap_minutes)

        schedule = DailySchedule(
            date=current_date,
            work_start=work_start,
            work_end=work_end,
            lunch_start=lunch_start,
            lunch_duration_minutes=lunch_dur,
            sessions=tuple(sessions),
        )

        logger.info(
            "Generated schedule for %s: %d sessions, start %s, end %s",
            schedule.date,
            len(schedule.sessions),
            schedule.work_start,
            schedule.work_end,
        )
        return schedule
