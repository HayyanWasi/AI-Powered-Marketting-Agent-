"""LinkedIn Human Behavior Scheduler.

Plans the day dynamically using HumanSchedule and spawns lightweight
non-blocking session executors using APScheduler date triggers.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config.settings import settings
from src.modules.linkedin.models import AutoPilotConfig, SessionWindow
from src.modules.linkedin.worker.human_schedule import HumanSchedule
from src.modules.linkedin.worker.post_publisher import publish_due_posts
from src.modules.linkedin.worker.review_queue import ReviewQueue
from src.modules.linkedin.worker.session_executor import SessionExecutor
from src.modules.linkedin.worker.warmup_manager import WarmupManager

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_engagement_active = settings.linkedin_auto_engagement_enabled


def get_scheduler() -> AsyncIOScheduler:
    """Singleton getter for AsyncIOScheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def _trigger_session(
    account_id: str,
    timezone: str,
    session: SessionWindow,
    invite_limit: int,
    like_limit: int,
    comment_limit: int,
) -> None:
    """Non-blocking trigger for a specific session burst."""
    if not _engagement_active:
        logger.info("LinkedIn engagement session skipped because autopilot is paused.")
        return
    logger.info("Triggering session for %s at %s", account_id, session.start)

    executor = SessionExecutor(account_id, timezone)

    # Run in background without blocking the scheduler
    asyncio.create_task(
        executor.execute_session(
            session,
            daily_invite_limit=invite_limit,
            daily_like_limit=like_limit,
            daily_comment_limit=comment_limit,
        )
    )

    # Also trigger cleanup of stale review queue drafts here since it's a good periodic spot
    queue = ReviewQueue()
    queue.expire_stale(hours=48)


async def _plan_and_schedule_day() -> None:
    """Daily planner job run every morning (e.g., at 1:00 AM)."""
    if not _engagement_active:
        logger.info("LinkedIn engagement planning skipped because autopilot is paused.")
        return
    account_id = settings.unipile_account_id
    if not account_id or account_id == "your_linked_linkedin_account_id":
        logger.info("Human Scheduler skipped: UNIPILE_ACCOUNT_ID not configured.")
        return

    logger.info("Planning daily LinkedIn schedule for account %s...", account_id)

    config = AutoPilotConfig(
        daily_invite_limit=settings.linkedin_daily_invite_limit,
        daily_like_limit=settings.linkedin_daily_like_limit,
        daily_comment_limit=settings.linkedin_daily_comment_limit,
        timezone=settings.linkedin_timezone,
    )
    warmup_manager = WarmupManager(account_id)

    # 1. Evaluate limits
    warmup_state = warmup_manager.evaluate_daily_limits(
        config.daily_invite_limit, config.daily_like_limit + config.daily_comment_limit
    )
    configured_engagement_total = config.daily_like_limit + config.daily_comment_limit
    session_like_limit = min(
        config.daily_like_limit,
        round(
            warmup_state.current_daily_engage_limit
            * config.daily_like_limit
            / configured_engagement_total
        ),
    )
    session_comment_limit = min(
        config.daily_comment_limit,
        warmup_state.current_daily_engage_limit - session_like_limit,
    )

    # 2. Build human schedule
    planner = HumanSchedule()
    schedule = planner.plan_and_schedule_day(config, warmup_state)

    # 3. Queue APScheduler date triggers for today's sessions
    sched = get_scheduler()
    for session in schedule.sessions:
        # Construct full datetime for session start
        session_dt = datetime.combine(schedule.date, session.start)

        # If the generated time is accidentally in the past (e.g. running planner late), adjust
        if session_dt < datetime.now():
            session_dt = datetime.now()

        sched.add_job(
            _trigger_session,
            "date",
            run_date=session_dt,
            args=[
                account_id,
                config.timezone,
                session,
                warmup_state.current_daily_invite_limit,
                session_like_limit,
                session_comment_limit,
            ],
            id=f"session_{account_id}_{session_dt.strftime('%H%M%S')}",
            replace_existing=True,
        )

    logger.info("Successfully queued %d sessions for today.", len(schedule.sessions))


def set_engagement_active(active: bool) -> None:
    """Pause or resume real engagement jobs for the configured account."""
    global _engagement_active
    _engagement_active = active and settings.linkedin_auto_engagement_enabled

    scheduler = get_scheduler()
    if not scheduler.running:
        return

    for job in scheduler.get_jobs():
        if job.id.startswith("session_") or job.id == "linkedin_daily_planner_resume":
            job.remove()

    if _engagement_active:
        scheduler.add_job(
            _plan_and_schedule_day,
            "date",
            run_date=datetime.now(),
            id="linkedin_daily_planner_resume",
            replace_existing=True,
        )


def start_linkedin_scheduler() -> None:
    """Start the APScheduler background worker if not already running."""
    scheduler = get_scheduler()
    if not scheduler.running:
        if settings.linkedin_auto_engagement_enabled:
            scheduler.add_job(
                _plan_and_schedule_day,
                "cron",
                hour=1,
                minute=0,
                id="linkedin_daily_planner",
                replace_existing=True,
            )

        # Post Publisher: every 5 minutes
        # Polls linkedin_posts for rows where status='scheduled' AND scheduled_at <= now()
        # and dispatches them to Unipile. This is what makes campaign posts go live on time.
        scheduler.add_job(
            publish_due_posts,
            "interval",
            minutes=5,
            id="linkedin_post_publisher",
            replace_existing=True,
        )

        from src.modules.linkedin.worker.comment_sync import start_comment_sync_job
        scheduler.add_job(
            start_comment_sync_job,
            "interval",
            minutes=5,
            id="linkedin_comment_sync",
            replace_existing=True,
        )

        scheduler.start()

        if settings.linkedin_auto_engagement_enabled:
            scheduler.add_job(_plan_and_schedule_day, "date", run_date=datetime.now())

        # On startup: immediately check for any posts that became due while server was down
        scheduler.add_job(
            publish_due_posts,
            "date",
            run_date=datetime.now(),
            id="linkedin_post_publisher_startup",
        )

        logger.info(
            "LinkedIn Scheduler started: post publisher runs every 5 min; "
            "engagement planner is configuration-controlled."
        )


def shutdown_linkedin_scheduler() -> None:
    """Gracefully shutdown the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("LinkedIn Human Behavior Scheduler shut down.")
