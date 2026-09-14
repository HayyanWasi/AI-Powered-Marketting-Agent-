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
from datetime import UTC, datetime

from src.config.settings import settings
from src.gateways.unipile_gateway import get_unipile_gateway
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
    account_id = settings.unipile_account_id
    if not account_id or account_id in ("your_linked_linkedin_account_id", ""):
        logger.info("[POST PUBLISHER] Skipped: UNIPILE_ACCOUNT_ID not configured.")
        return {"published": 0, "failed": 0, "skipped": 0}

    posts_repo = BaseRepository("linkedin_posts")
    gateway = get_unipile_gateway()

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
        full_content = post.get("full_content") or ""

        if not full_content.strip():
            logger.warning("[POST PUBLISHER] Post %s has empty content — marking failed.", post_id)
            _mark_failed(posts_repo, post_id, "Empty post content")
            summary["failed"] += 1
            continue

        logger.info(
            "[POST PUBLISHER] Publishing post %s (scheduled_at=%s) — %.80s…",
            post_id,
            post.get("scheduled_at"),
            full_content,
        )

        try:
            unipile_post_id = await gateway.create_post(account_id, full_content)
        except Exception as exc:
            logger.error("[POST PUBLISHER] Exception publishing post %s: %s", post_id, exc)
            _mark_failed(posts_repo, post_id, str(exc))
            summary["failed"] += 1
            continue

        if unipile_post_id:
            _mark_published(posts_repo, post_id, unipile_post_id)
            summary["published"] += 1
            logger.info(
                "[POST PUBLISHER] ✅ Post %s published to LinkedIn. Unipile ID: %s",
                post_id,
                unipile_post_id,
            )
        else:
            _mark_failed(posts_repo, post_id, "Unipile returned no post ID (possible API error)")
            summary["failed"] += 1
            logger.warning("[POST PUBLISHER] ❌ Post %s failed — Unipile returned None.", post_id)

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
