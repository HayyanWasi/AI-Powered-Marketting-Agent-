"""Fail-Closed Engagement Stale Claim Recovery.

Identifies and recovers engagement log items that were claimed by a worker
(status = 'claimed') but never finalized due to process crash, timeout, or
unhandled exception.

Rules:
- NEVER retry Unipile
- NEVER return item to pending or delete it
- NEVER remove permanent deduplication protection (unique index covers all statuses)
- Compare-and-Set (CAS): only update while status is still 'claimed'
- Gated behind settings.linkedin_enable_stale_recovery for live safety.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from src.config.settings import settings
from src.config.supabase import get_supabase_client
from src.modules.linkedin.models import EngagementLogStatus
from src.utils.sanitizer import sanitize_error_message

logger = logging.getLogger(__name__)


def recover_stale_engagement_claims(
    client: Any | None = None,
    stale_minutes: int | None = None,
    force: bool = False,
) -> int:
    """Fail-closed recovery for engagement claims stuck in 'claimed'.

    A claim that has remained 'claimed' longer than ``stale_minutes`` (default 15)
    almost certainly belongs to a worker that crashed or timed out before recording
    a final result.

    To preserve permanent deduplication constraints and avoid re-dispatching
    duplicate likes, comments, or connection requests, these claims are
    transitioned atomically to 'needs_review'.

    Safety:
    - Periodic scheduler invocation is prepared behind ``settings.linkedin_enable_stale_recovery``.

    Returns the number of claims recovered to 'needs_review'.
    """
    client = client or get_supabase_client()
    stale_mins = (
        stale_minutes
        if stale_minutes is not None
        else getattr(settings, "linkedin_engagement_stale_minutes", 15)
    )
    cutoff_dt = datetime.now(UTC) - timedelta(minutes=stale_mins)
    cutoff_iso = cutoff_dt.isoformat()

    try:
        # Bounded query for stale claims
        res = (
            client.table("linkedin_engagement_log")
            .select("id,created_at,company_profile_id,action_type")
            .eq("status", EngagementLogStatus.CLAIMED.value)
            .lte("created_at", cutoff_iso)
            .limit(100)
            .execute()
        )
        stale_rows = res.data or []
    except Exception as e:
        logger.error("[ENGAGEMENT RECOVERY] Failed to query stale engagement claims: %s", e)
        return 0

    if not stale_rows:
        return 0

    recovered = 0
    now_iso = datetime.now(UTC).isoformat()
    sanitized_reason = (
        sanitize_error_message("Stale claim: worker interrupted before completion")
        or "Stale claim: worker interrupted before completion"
    )

    for row in stale_rows:
        claim_id = row.get("id")
        created_at = row.get("created_at")
        try:
            # CAS: only update if status is still 'claimed'
            upd = (
                client.table("linkedin_engagement_log")
                .update(
                    {
                        "status": EngagementLogStatus.NEEDS_REVIEW.value,
                        "completed_at": now_iso,
                        "error_message": sanitized_reason,
                    }
                )
                .eq("id", claim_id)
                .eq("status", EngagementLogStatus.CLAIMED.value)
                .execute()
            )
            if upd.data:
                recovered += 1
                logger.warning(
                    "[ENGAGEMENT RECOVERY] Stale claim %s (%s) created at %s "
                    "exceeded %d min -> needs_review. Permanent dedupe preserved.",
                    claim_id,
                    row.get("action_type"),
                    created_at,
                    stale_mins,
                )
        except Exception as e:
            logger.error(
                "[ENGAGEMENT RECOVERY] Failed to park stale claim %s in needs_review: %s",
                claim_id,
                e,
            )

    if recovered:
        logger.warning(
            "[ENGAGEMENT RECOVERY] Fail-closed recovery parked %d stale claim(s) in needs_review.",
            recovered,
        )
    return recovered
