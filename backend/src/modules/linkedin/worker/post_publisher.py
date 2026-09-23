"""Post Publisher Worker — Dispatches due scheduled LinkedIn posts via Unipile.

Runs every 5 minutes (triggered by APScheduler).  Queries ``linkedin_posts``
for rows where ``status = 'scheduled'`` and ``scheduled_at <= now()``, then
publishes each one via ``UnipileGateway.create_post()``.

Design decisions:
- Each post is dispatched individually with a small delay between them to
  mimic human behaviour and avoid Unipile rate limits.
- On success the row is updated to ``status = 'published'`` with the returned
  Unipile post_id.
- On failure the row gets ``status = 'failed'`` with an error note so the
  operator can retry manually.
- The worker is intentionally stateless: it relies purely on DB state, so
  it is safe to restart at any time.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from src.config.settings import settings
from src.gateways.unipile_gateway import UnipileTransportError, get_unipile_gateway
from src.modules.linkedin.models import PostStatus
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

# How many posts to dispatch in a single run (safety cap per poll cycle)
_MAX_POSTS_PER_RUN = 5
# Seconds to sleep between individual post publications
_INTER_POST_DELAY_SECONDS = 15


async def publish_due_posts() -> dict[str, int]:
    """Find and publish all LinkedIn posts whose scheduled_at has arrived.

    Returns a summary dict: ``{published, failed, skipped}``.
    """
    posts_repo = BaseRepository("linkedin_posts")
    gateway = get_unipile_gateway()

    # Fail-closed recovery: park any claim that crashed mid-publish BEFORE we
    # claim new work. This never calls Unipile and never resets to 'scheduled'.
    recover_stale_publishing(posts_repo)

    now_iso = datetime.now(UTC).isoformat()

    # Fetch all SCHEDULED posts whose time has come
    try:
        res = (
            posts_repo.client.table("linkedin_posts")
            .select("*")
            .eq("status", "scheduled")
            .lte("scheduled_at", now_iso)
            .order("scheduled_at", desc=False)
            .limit(_MAX_POSTS_PER_RUN)
            .execute()
        )
        due_posts = res.data or []
    except Exception as e:
        logger.error("[POST PUBLISHER] Failed to query due posts: %s", e)
        return {"published": 0, "failed": 0, "skipped": 0}

    if not due_posts:
        logger.debug("[POST PUBLISHER] No due posts found at %s", now_iso)
        return {"published": 0, "failed": 0, "skipped": 0}

    logger.info("[POST PUBLISHER] Found %d due post(s) to publish.", len(due_posts))

    summary = {"published": 0, "failed": 0, "skipped": 0}

    for post in due_posts:
        post_id = post.get("id", "?")

        # Atomically claim the post (scheduled -> publishing). Only one
        # worker/process can win this race, so a post is never published twice.
        if not _claim_post(posts_repo, post_id):
            logger.info(
                "[POST PUBLISHER] Post %s already claimed by another worker — skipping.",
                post_id,
            )
            summary["skipped"] += 1
            continue

        account_id = post.get("linkedin_account_id")
        full_content = post.get("full_content") or ""

        if not account_id:
            logger.error("[POST PUBLISHER] Post %s has no bound LinkedIn account.", post_id)
            _mark_failed(posts_repo, post_id, "No LinkedIn account is bound to this post")
            summary["failed"] += 1
            continue

        if not full_content.strip():
            logger.warning("[POST PUBLISHER] Post %s has empty content — marking failed.", post_id)
            _mark_failed(posts_repo, post_id, "Empty post content")
            summary["failed"] += 1
            continue

        res = await execute_post_publish(
            posts_repo,
            gateway,
            post_id,
            account_id,
            full_content,
            media_url=post.get("media_url"),
        )
        if res.get("status") == PostStatus.PUBLISHED.value:
            summary["published"] += 1
        elif res.get("status") in (PostStatus.FAILED.value, PostStatus.NEEDS_REVIEW.value):
            summary["failed"] += 1

        # Human-like delay between posts
        if len(due_posts) > 1:
            await asyncio.sleep(_INTER_POST_DELAY_SECONDS)

    logger.info(
        "[POST PUBLISHER] Run complete — published=%d failed=%d skipped=%d",
        summary["published"],
        summary["failed"],
        summary["skipped"],
    )
    return summary


def _claim_post(repo: BaseRepository, post_id: str) -> bool:
    """Atomically move one post from 'scheduled' to 'publishing'.

    Returns True only if THIS call performed the transition. The update is
    guarded by ``status = 'scheduled'`` so it succeeds for exactly one caller;
    any concurrent worker (or the startup job racing the interval job) sees the
    row already in 'publishing'/'published' and its guarded update matches no
    rows, returning False. This is the sole duplicate-publish guard.

    ``publishing_started_at`` is stamped in the SAME atomic update so stale-claim
    recovery can tell how long a post has been in flight.
    """
    try:
        res = (
            repo.client.table("linkedin_posts")
            .update(
                {
                    "status": PostStatus.PUBLISHING.value,
                    "publishing_started_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", post_id)
            .eq("status", PostStatus.SCHEDULED.value)
            .execute()
        )
        return bool(res.data)
    except Exception as e:
        logger.error("[POST PUBLISHER] Failed to claim post %s: %s", post_id, e)
        return False


def recover_stale_publishing(repo: BaseRepository | None = None) -> int:
    """Fail-closed recovery for claims stuck in 'publishing'.

    A post that stayed 'publishing' longer than
    ``settings.linkedin_publish_stale_minutes`` almost certainly belongs to a
    worker that crashed mid-publish. This Unipile deployment cannot reconcile
    whether the remote post was actually created (no post-listing/search by
    author, no idempotency key), so auto-retrying could duplicate the post.

    Therefore such rows are parked in ``needs_review`` for manual inspection.
    This function NEVER calls Unipile and NEVER transitions
    ``publishing -> scheduled``. Fresh claims (under the threshold) and rows
    without a ``publishing_started_at`` timestamp are left untouched.

    Returns the number of rows moved to ``needs_review``.
    """
    repo = repo or BaseRepository("linkedin_posts")
    cutoff = (
        datetime.now(UTC) - timedelta(minutes=settings.linkedin_publish_stale_minutes)
    ).isoformat()

    try:
        res = (
            repo.client.table("linkedin_posts")
            .select("id,publishing_started_at")
            .eq("status", PostStatus.PUBLISHING.value)
            .lte("publishing_started_at", cutoff)
            .execute()
        )
        stale = res.data or []
    except Exception as e:
        logger.error("[POST PUBLISHER] Failed to query stale publishing posts: %s", e)
        return 0

    recovered = 0
    for row in stale:
        post_id = row.get("id")
        try:
            # Guarded by status='publishing' so we never clobber a row that a
            # worker just finished (published/failed) in parallel.
            upd = (
                repo.client.table("linkedin_posts")
                .update({"status": PostStatus.NEEDS_REVIEW.value})
                .eq("id", post_id)
                .eq("status", PostStatus.PUBLISHING.value)
                .execute()
            )
            if upd.data:
                recovered += 1
                logger.warning(
                    "[POST PUBLISHER] Stale claim: post %s in 'publishing' since %s "
                    "exceeded %d min -> needs_review (reason=remote_publish_state_unknown). "
                    "NOT auto-republished; manual review required.",
                    post_id,
                    row.get("publishing_started_at"),
                    settings.linkedin_publish_stale_minutes,
                )
        except Exception as e:
            logger.error(
                "[POST PUBLISHER] Failed to park stale post %s in needs_review: %s",
                post_id,
                e,
            )

    if recovered:
        logger.warning(
            "[POST PUBLISHER] Fail-closed recovery parked %d stale post(s) in needs_review.",
            recovered,
        )
    return recovered


def _mark_published(repo: BaseRepository, post_id: str, unipile_post_id: str) -> None:
    """Update linkedin_posts row to 'published'."""
    try:
        repo.client.table("linkedin_posts").update(
            {
                "status": "published",
                "unipile_post_id": unipile_post_id,
                "published_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", post_id).execute()
    except Exception as e:
        logger.error("[POST PUBLISHER] Failed to mark post %s as published: %s", post_id, e)


def _mark_failed(repo: BaseRepository, post_id: str, reason: str) -> None:
    """Update linkedin_posts row to 'failed'."""
    try:
        repo.client.table("linkedin_posts").update(
            {
                "status": "failed",
                "published_at": None,
            }
        ).eq("id", post_id).execute()
    except Exception as e:
        logger.error("[POST PUBLISHER] Failed to mark post %s as failed: %s", post_id, e)


def _mark_needs_review(repo: BaseRepository, post_id: str, reason: str = "") -> None:
    """Update linkedin_posts row to 'needs_review'."""
    try:
        repo.client.table("linkedin_posts").update(
            {
                "status": PostStatus.NEEDS_REVIEW.value,
            }
        ).eq("id", post_id).execute()
    except Exception as e:
        logger.error("[POST PUBLISHER] Failed to mark post %s as needs_review: %s", post_id, e)


async def execute_post_publish(
    repo: BaseRepository,
    gateway: Any,
    post_id: str,
    account_id: str,
    full_content: str,
    media_url: str | None = None,
) -> dict[str, Any]:
    """Execute external dispatch, DB finalization, and failure classification.

    Shared between scheduled worker (`publish_due_posts`) and Publish Now.
    Assumes the row has ALREADY been atomically claimed into 'publishing'.

    Rules:
    - External dispatch via gateway.create_post.
    - Ambiguous transport failure / timeout:
        -> mark needs_review (never automatically retry).
    - Confirmed provider rejection (gateway returns None):
        -> mark failed.
    - External success:
        -> attempt DB finalization (status='published', unipile_post_id, published_at).
        -> if DB finalization fails: do NOT re-dispatch. Best effort: mark needs_review.
           If even that fails, leave in 'publishing' (stale recovery will catch it).
           Never return to draft.
    """
    logger.info(
        "[POST PUBLISHER] Publishing post %s to account %s — %.80s…",
        post_id,
        account_id,
        full_content,
    )

    try:
        unipile_post_id = await gateway.create_post(
            account_id, full_content, media_url=media_url
        )
    except (TimeoutError, UnipileTransportError, httpx.RequestError) as exc:
        logger.error(
            "[POST PUBLISHER] Ambiguous transport failure publishing post %s: %s",
            post_id,
            exc,
        )
        _mark_needs_review(repo, post_id, f"Transport error / timeout: {exc}")
        return {
            "status": PostStatus.NEEDS_REVIEW.value,
            "success": False,
            "unipile_post_id": None,
            "error": f"Ambiguous transport failure: {exc}",
        }
    except Exception as exc:
        logger.error(
            "[POST PUBLISHER] Unexpected exception publishing post %s: %s",
            post_id,
            exc,
        )
        _mark_failed(repo, post_id, str(exc))
        return {
            "status": PostStatus.FAILED.value,
            "success": False,
            "unipile_post_id": None,
            "error": str(exc),
        }

    # Gateway returned None: confirmed provider rejection per gateway contract
    if not unipile_post_id:
        logger.warning(
            "[POST PUBLISHER] ❌ Post %s failed — provider rejected request.",
            post_id,
        )
        _mark_failed(repo, post_id, "Provider rejected request (Unipile returned no post ID)")
        return {
            "status": PostStatus.FAILED.value,
            "success": False,
            "unipile_post_id": None,
            "error": "Provider rejected request (Unipile returned no post ID)",
        }

    # External success -> DB finalization
    published_at = datetime.now(UTC).isoformat()
    try:
        res = (
            repo.client.table("linkedin_posts")
            .update(
                {
                    "status": PostStatus.PUBLISHED.value,
                    "unipile_post_id": unipile_post_id,
                    "published_at": published_at,
                }
            )
            .eq("id", post_id)
            .execute()
        )
        post_row = res.data[0] if (res.data and len(res.data) > 0) else None
        if not post_row:
            raise RuntimeError(f"Post {post_id} finalization update matched 0 rows")

        logger.info(
            "[POST PUBLISHER] ✅ Post %s published to LinkedIn. Unipile ID: %s",
            post_id,
            unipile_post_id,
        )
        return {
            "status": PostStatus.PUBLISHED.value,
            "success": True,
            "unipile_post_id": unipile_post_id,
            "published_at": published_at,
            "post": post_row,
        }
    except Exception as db_err:
        logger.critical(
            "[POST PUBLISHER] External post succeeded (unipile_id=%s) but DB finalization failed for post %s: %s",
            unipile_post_id,
            post_id,
            db_err,
        )
        # External success + local DB finalization failure:
        # Do NOT dispatch again.
        # Best effort: set needs_review.
        # If even that DB mutation fails: leave in 'publishing'.
        # Never return it to draft automatically.
        try:
            repo.client.table("linkedin_posts").update(
                {
                    "status": PostStatus.NEEDS_REVIEW.value,
                    "unipile_post_id": unipile_post_id,
                }
            ).eq("id", post_id).execute()
        except Exception as fallback_err:
            logger.error(
                "[POST PUBLISHER] Failed to park post %s in needs_review: %s. Leaving in publishing.",
                post_id,
                fallback_err,
            )

        return {
            "status": PostStatus.NEEDS_REVIEW.value,
            "success": False,
            "unipile_post_id": unipile_post_id,
            "error": f"External publish succeeded but local database update failed: {db_err}",
        }
