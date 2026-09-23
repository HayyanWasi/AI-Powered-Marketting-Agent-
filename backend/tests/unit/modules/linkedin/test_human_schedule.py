from datetime import UTC, datetime

from src.modules.linkedin.models import AutoPilotConfig, WarmupState
from src.modules.linkedin.worker.human_schedule import HumanSchedule


def test_human_schedule_generation_bounds():
    planner = HumanSchedule()
    config = AutoPilotConfig(
        sessions_per_day_min=3,
        sessions_per_day_max=5,
        work_start_earliest=8,
        work_end_latest=18,
    )
    # A warmup state indicating the account is allowed 10 invites and 15 engages (likes+comments)
    warmup = WarmupState(
        linkedin_account_id="test", current_daily_invite_limit=10, current_daily_engage_limit=15
    )

    schedule = planner.plan_and_schedule_day(config, warmup, datetime.now(UTC))

    # Verify session count bounds
    assert config.sessions_per_day_min <= len(schedule.sessions) <= config.sessions_per_day_max

    total_actions = sum(s.max_actions for s in schedule.sessions)
    # Verify total actions matches the warmup quota (10 + 15 = 25)
    assert total_actions == 25

    # Verify sessions don't overlap with lunch
    assert schedule.lunch_start is not None
    assert schedule.lunch_duration_minutes > 0
    # Rough check that sessions start after work_start and end before work_end
    for session in schedule.sessions:
        assert session.start >= schedule.work_start
        assert session.end <= schedule.work_end
