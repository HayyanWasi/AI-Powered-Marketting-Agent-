"""LinkedIn Human Behavior Multi-Tenant Scheduler.

Processes eligible brands independently with dedicated PostgreSQL session-level
advisory locking (pg_try_advisory_lock / pg_advisory_unlock) and per-brand quotas.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config.supabase import get_supabase_client
from src.modules.linkedin.account_resolver import resolve_brand_linkedin_account
from src.modules.linkedin.distributed_lock import BrandAdvisoryLock
from src.modules.linkedin.models import SessionWindow
from src.modules.linkedin.worker.post_publisher import publish_due_posts
from src.modules.linkedin.worker.review_queue import ReviewQueue
from src.modules.linkedin.worker.session_executor import SessionExecutor
from src.modules.linkedin.worker.target_resolver import TargetResolver
from src.modules.linkedin.worker.warmup_manager import WarmupManager

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Singleton getter for AsyncIOScheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def _run_brand_session(
    brand_id: str,
    user_id: str,
    account: dict[str, Any],
    settings_row: dict[str, Any],
    session: SessionWindow,
    invite_limit: int,
    like_limit: int,
    comment_limit: int,
    action_types: tuple[str, ...],
) -> None:
    """Execute a single burst for a brand within a dedicated session advisory lock."""
    lock = BrandAdvisoryLock(brand_id)
    acquired = await lock.acquire()
    if not acquired:
        logger.info(
            "Brand %s engagement session skipped: advisory lock unavailable or failed closed; zero actions dispatched.",
            brand_id,
        )
        return

    try:
        executor = SessionExecutor(
            account_id=str(account["id"]),
            unipile_account_id=str(account["unipile_account_id"]),
            company_profile_id=brand_id,
            user_id=user_id,
            timezone=settings_row.get("timezone", "UTC"),
            connection_note_template=settings_row.get("connection_note_template", ""),
        )
        await executor.execute_session(
            session=session,
            daily_invite_limit=invite_limit,
            daily_like_limit=like_limit,
            daily_comment_limit=comment_limit,
            allowed_action_types=action_types,
        )
    except Exception as e:
        logger.error("Error executing engagement session for brand %s: %s", brand_id, e)
    finally:
        await lock.release()


async def _plan_and_schedule_day() -> None:
    """Multi-tenant daily engagement loop: iterates through active brands."""
    client = get_supabase_client()
    try:
        res = (
            client.table("linkedin_engagement_settings")
            .select("*")
            .eq("engagement_enabled", True)
            .execute()
        )
        active_settings = res.data or []
    except Exception as e:
        logger.warning("Failed to query active engagement settings: %s", e)
        return

    if not active_settings:
        logger.debug("No brands with engagement_enabled=True found.")
        return

    logger.info("Found %d brand(s) with engagement enabled. Processing...", len(active_settings))

    # Cap concurrency to 5 parallel brand tasks to prevent DB connection pool exhaustion
    sem = asyncio.Semaphore(5)

    async def _process_brand(s_row: dict[str, Any]) -> None:
        async with sem:
            brand_id = s_row.get("company_profile_id")
            user_id = s_row.get("user_id")
            if not brand_id or not user_id:
                return

            account, reason = await resolve_brand_linkedin_account(brand_id, user_id)
            if not account:
                logger.info("Brand %s engagement skipped: %s", brand_id, reason)
                return

            auto_like = s_row.get("auto_like_enabled", False)
            auto_comment = s_row.get("auto_comment_generation_enabled", False)
            auto_connect = s_row.get("auto_connect_enabled", False)

            action_types = []
            if auto_comment:
                action_types.append("comment")
            if auto_like:
                action_types.append("like")
            if auto_connect:
                action_types.append("invite")

            if not action_types:
                logger.info("Brand %s has no engagement action types enabled; skipping.", brand_id)
                return

            account_id = str(account["id"])

            # Check personas: zero personas = safe no-op
            target_resolver = TargetResolver()
            personas = await target_resolver.load_personas(company_profile_id=str(brand_id))
            if not personas:
                logger.info(
                    "Brand %s has 0 active personas; skipping engagement (safe no-op).", brand_id
                )
                return

            warmup_manager = WarmupManager(account_id)
            warmup_state = warmup_manager.evaluate_daily_limits(
                s_row.get("invites_per_day", 10),
                s_row.get("likes_per_day", 15) + s_row.get("comments_per_day", 5),
            )

            invite_limit = min(
                s_row.get("invites_per_day", 10), warmup_state.current_daily_invite_limit
            )
            like_limit = min(
                s_row.get("likes_per_day", 15), warmup_state.current_daily_engage_limit
            )
            comment_limit = min(
                s_row.get("comments_per_day", 5), warmup_state.current_daily_engage_limit
            )

            session = SessionWindow(
                start=datetime.now().time(),
                end=(datetime.now() + timedelta(minutes=30)).time(),
                max_actions=min(10, invite_limit + like_limit + comment_limit),
                action_types=tuple(action_types),
            )

            await _run_brand_session(
                brand_id=str(brand_id),
                user_id=str(user_id),
                account=account,
                settings_row=s_row,
                session=session,
                invite_limit=invite_limit,
                like_limit=like_limit,
                comment_limit=comment_limit,
                action_types=tuple(action_types),
            )

    # Periodic cleanup of stale review queue items
    queue = ReviewQueue()
    queue.expire_stale(hours=48)

    await asyncio.gather(*[_process_brand(s) for s in active_settings], return_exceptions=True)


def set_engagement_active(active: bool) -> None:
    """Pause or resume real engagement jobs across the scheduler."""
    pass  # In the multi-tenant model, activation is controlled per-brand in linkedin_engagement_settings


def trigger_immediate_engagement_run() -> None:
    """Trigger an immediate one-shot execution of the engagement planner when Master Automation turns ON.

    Uses replace_existing=True to prevent duplicate queued triggers.
    Advisory locking inside _run_brand_session guarantees mutual exclusion per brand.
    """
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.add_job(
            _plan_and_schedule_day,
            "date",
            run_date=datetime.now(),
            id="linkedin_engagement_planner_immediate",
            replace_existing=True,
        )
        logger.info("Immediate engagement run scheduled following Master Automation ON toggle.")


def start_linkedin_scheduler() -> None:
    """Start the APScheduler background worker if not already running."""
    scheduler = get_scheduler()
    if not scheduler.running:
        # Engagement Planner: runs every 30 minutes
        scheduler.add_job(
            _plan_and_schedule_day,
            "interval",
            minutes=30,
            id="linkedin_engagement_planner",
            replace_existing=True,
        )

        # Post Publisher: every 5 minutes (UNTOUCHED)
        scheduler.add_job(
            publish_due_posts,
            "interval",
            minutes=5,
            id="linkedin_post_publisher",
            replace_existing=True,
        )

        # Comment Sync: every 5 minutes (UNTOUCHED)
        from src.modules.linkedin.worker.comment_sync import start_comment_sync_job

        scheduler.add_job(
            start_comment_sync_job,
            "interval",
            minutes=5,
            id="linkedin_comment_sync",
            replace_existing=True,
        )

        # Engagement Stale Recovery: prepared behind disabled flag (SAFETY OVERRIDE)
        from src.config.settings import settings

        if getattr(settings, "linkedin_enable_stale_recovery", False):
            from src.modules.linkedin.worker.engagement_recovery import (
                recover_stale_engagement_claims,
            )

            scheduler.add_job(
                recover_stale_engagement_claims,
                "interval",
                minutes=5,
                id="linkedin_engagement_stale_recovery",
                replace_existing=True,
            )

        scheduler.start()

        # On startup: check for due posts (UNTOUCHED)
        scheduler.add_job(
            publish_due_posts,
            "date",
            run_date=datetime.now(),
            id="linkedin_post_publisher_startup",
        )

        logger.info(
            "LinkedIn Scheduler started: post publisher runs every 5 min; "
            "multi-tenant engagement planner runs every 30 min."
        )


def shutdown_linkedin_scheduler() -> None:
    """Gracefully shutdown the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("LinkedIn Human Behavior Scheduler shut down.")
