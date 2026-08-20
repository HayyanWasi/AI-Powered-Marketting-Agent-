"""APScheduler integration for running AutoPilot Worker daily at 09:00 AM."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config.settings import settings
from src.modules.linkedin.worker.autopilot_worker import AutoPilotWorker

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Singleton getter for AsyncIOScheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def _scheduled_autopilot_job() -> None:
    """Trigger job wrapper called daily by scheduler."""
    account_id = settings.unipile_account_id
    if not account_id or account_id == "your_linked_linkedin_account_id":
        logger.info("AutoPilot scheduled job skipped: UNIPILE_ACCOUNT_ID not configured.")
        return

    logger.info("Starting scheduled daily AutoPilot run for account %s...", account_id)
    worker = AutoPilotWorker()
    res = await worker.execute_daily_run(account_id)
    logger.info("AutoPilot run completed: %s", res)


def start_linkedin_scheduler() -> None:
    """Start the APScheduler background worker if not already running."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.add_job(
            _scheduled_autopilot_job,
            "cron",
            hour=9,
            minute=0,
            id="linkedin_autopilot_daily",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("LinkedIn AutoPilot Scheduler started (Daily run set for 09:00 AM).")


def shutdown_linkedin_scheduler() -> None:
    """Gracefully shutdown the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("LinkedIn AutoPilot Scheduler shut down.")
