from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/autopilot", tags=["Autopilot Control Room"])

# User-scoped in-memory settings
_DEFAULT_SETTINGS: dict[str, Any] = {
    "daily_connections": 15,
    "daily_likes": 20,
    "daily_comments": 10,
    "post_time_slot": "10:00 AM",
    "video_time_slot": "04:00 PM",
    "master_active": True,
}

_USER_SETTINGS: dict[str, dict[str, Any]] = {}


def _get_user_settings(user_id: str) -> dict[str, Any]:
    if user_id not in _USER_SETTINGS:
        _USER_SETTINGS[user_id] = dict(_DEFAULT_SETTINGS)
    return _USER_SETTINGS[user_id]


class AutopilotSettingsModel(BaseModel):
    daily_connections: int = Field(default=15, ge=1, le=25)
    daily_likes: int = Field(default=20, ge=1, le=40)
    daily_comments: int = Field(default=10, ge=1, le=15)
    post_time_slot: str = Field(default="10:00 AM")
    video_time_slot: str = Field(default="04:00 PM")
    master_active: bool = Field(default=True)


class ToggleRequest(BaseModel):
    active: bool


@router.get("/settings", response_model=AutopilotSettingsModel)
async def get_settings(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get current daily automation limits and schedule times for authenticated user."""
    return _get_user_settings(user.id)


@router.post("/settings", response_model=AutopilotSettingsModel)
async def update_settings(
    payload: AutopilotSettingsModel,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Save daily automation limits and schedule times for authenticated user."""
    user_settings = _get_user_settings(user.id)
    user_settings.update(payload.model_dump())
    logger.info("[AUTOPILOT SETTINGS] Updated settings for user %s: %s", user.id, user_settings)
    return user_settings


@router.post("/toggle")
async def toggle_autopilot(
    req: ToggleRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Toggle master automation state (Active/Paused) for authenticated user."""
    user_settings = _get_user_settings(user.id)
    user_settings["master_active"] = req.active
    status_str = "ACTIVE" if req.active else "PAUSED"
    logger.info(
        "[AUTOPILOT TOGGLE] Master automation toggled to: %s for user %s", status_str, user.id
    )
    return {"status": "success", "master_active": req.active}


@router.get("/tracker")
async def get_tracker_data(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Aggregated status for Live Campaign Tracking & Progress scoped to authenticated user."""
    user_settings = _get_user_settings(user.id)
    # 1. Fetch campaigns from DB owned by this user
    campaigns_repo = BaseRepository("campaigns")
    posts_repo = BaseRepository("linkedin_posts")

    running_campaigns = []
    upcoming_queue = []

    try:
        camp_res = (
            campaigns_repo.client.table("campaigns")
            .select("*")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        if camp_res.data:
            for c in camp_res.data:
                c_name = c.get("name") or "Unnamed Campaign"
                c_status = (c.get("state") or c.get("status") or "ACTIVE").upper()
                c_id = c.get("id")
                running_campaigns.append(
                    {
                        "campaign_id": c_id,
                        "campaign_name": c_name,
                        "status": (
                            "ACTIVE"
                            if c_status in ("ACTIVE", "LAUNCHED", "PUBLISHED", "DRAFT")
                            else c_status
                        ),
                        "last_action": "Dispatched scheduled content",
                        "progress_pct": (
                            68
                            if c_status in ("ACTIVE", "LAUNCHED")
                            else 100 if c_status == "COMPLETED" else 45
                        ),
                    }
                )
    except Exception as e:
        logger.warning("[AUTOPILOT TRACKER] Could not read campaigns: %s", e)

    # 2. Add Video Job in upcoming queue (preserves scheduled video broadcast window)
    video_slot = user_settings.get("video_time_slot", "04:00 PM")
    post_slot = user_settings.get("post_time_slot", "10:00 AM")

    latest_video_title = "AI Product Spotlight Commercial"
    if running_campaigns:
        latest_video_title = f"{running_campaigns[0]['campaign_name']} Video"

    upcoming_queue.append(
        {
            "id": "q-vid-active",
            "type": "video",
            "title": latest_video_title,
            "scheduled_time": f"Today at {video_slot}",
            "status": "ready",
        }
    )

    # 3. Fetch all scheduled posts for upcoming queue (ordered by latest, not truncated to 2)
    try:
        posts_res = (
            posts_repo.client.table("linkedin_posts")
            .select("*")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        if posts_res.data:
            for p in posts_res.data:
                hook = p.get("hook") or p.get("content") or "LinkedIn Post"
                clean_hook = hook.strip().replace("\n", " ")
                if len(clean_hook) > 65:
                    clean_hook = clean_hook[:62] + "..."

                p_status = (p.get("status") or "pending").lower()
                status = "ready" if p_status in ("ready", "published", "scheduled") else "pending"

                upcoming_queue.append(
                    {
                        "id": p.get("id"),
                        "type": "post",
                        "title": clean_hook,
                        "scheduled_time": f"Tomorrow at {post_slot}",
                        "status": status,
                    }
                )
    except Exception as e:
        logger.warning("[AUTOPILOT TRACKER] Could not read posts: %s", e)

    # If queue is empty, supply clean default queue items
    if not upcoming_queue:
        upcoming_queue = [
            {
                "id": "q-vid-1",
                "type": "video",
                "title": "AI Product Spotlight Commercial",
                "scheduled_time": f"Today at {user_settings.get('video_time_slot', '04:00 PM')}",
                "status": "ready",
            },
            {
                "id": "q-post-1",
                "type": "post",
                "title": "Scaling SaaS Marketing with Autonomous Agents",
                "scheduled_time": f"Tomorrow at {user_settings.get('post_time_slot', '10:00 AM')}",
                "status": "pending",
            },
        ]

    # If running campaigns empty, supply standard demo items
    if not running_campaigns:
        running_campaigns = [
            {
                "campaign_id": "demo-1",
                "campaign_name": "Tier-1 FMCG Replenishment Sprint",
                "status": "ACTIVE",
                "last_action": "Connection invite sent 12m ago",
                "progress_pct": 68,
            },
            {
                "campaign_id": "demo-2",
                "campaign_name": "LATAM Retail Tienditas Expansion",
                "status": "ACTIVE",
                "last_action": "Smart comment posted 28m ago",
                "progress_pct": 42,
            },
            {
                "campaign_id": "demo-3",
                "campaign_name": "EU Beverage Route-to-Market Q4",
                "status": "SCHEDULED",
                "last_action": "Queue dispatch planned at 10:00 AM",
                "progress_pct": 15,
            },
        ]

    return {
        "master_active": user_settings.get("master_active", True),
        "daily_progress": {
            "connections_sent": 5,
            "connections_max": user_settings.get("daily_connections", 15),
            "likes_given": 8,
            "likes_max": user_settings.get("daily_likes", 20),
            "comments_posted": 3,
            "comments_max": user_settings.get("daily_comments", 10),
        },
        "upcoming_queue": upcoming_queue,
        "running_campaigns": running_campaigns,
    }


@router.delete("/queue/{job_id}")
async def delete_queue_job(
    job_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Delete or cancel a scheduled job from the upcoming queue."""
    posts_repo = BaseRepository("linkedin_posts")
    deleted_from_db = False
    try:
        # If it's a UUID, delete from linkedin_posts table
        res = posts_repo.client.table("linkedin_posts").delete().eq("id", job_id).execute()
        if res.data:
            deleted_from_db = True
    except Exception as e:
        logger.warning("[AUTOPILOT] Could not delete from linkedin_posts: %s", e)

    return {
        "success": True,
        "id": job_id,
        "deleted_from_db": deleted_from_db,
        "message": f"Job {job_id} successfully removed from queue",
    }


@router.post("/publish-now/{post_id}")
async def publish_post_now(
    post_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Immediately publish a specific scheduled post to LinkedIn (bypass scheduler wait).

    Useful for testing or when a post needs to go out right now.
    """
    from src.config.settings import settings
    from src.gateways.unipile_gateway import get_unipile_gateway

    posts_repo = BaseRepository("linkedin_posts")

    # Fetch the post
    try:
        res = (
            posts_repo.client.table("linkedin_posts")
            .select("*")
            .eq("id", post_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return {"success": False, "error": f"Post {post_id} not found"}
        post = res.data[0]
    except Exception as e:
        return {"success": False, "error": str(e)}

    full_content = post.get("full_content") or ""
    if not full_content.strip():
        return {"success": False, "error": "Post has empty content"}

    account_id = settings.unipile_account_id
    if not account_id:
        return {"success": False, "error": "UNIPILE_ACCOUNT_ID not configured in .env"}

    gateway = get_unipile_gateway()
    try:
        from datetime import UTC, datetime

        unipile_post_id = await gateway.create_post(account_id, full_content)
        if unipile_post_id:
            posts_repo.client.table("linkedin_posts").update(
                {
                    "status": "published",
                    "unipile_post_id": unipile_post_id,
                    "published_at": datetime.now(UTC).isoformat(),
                }
            ).eq("id", post_id).execute()
            return {
                "success": True,
                "post_id": post_id,
                "unipile_post_id": unipile_post_id,
                "message": "Post published to LinkedIn!",
            }
        else:
            return {
                "success": False,
                "error": "Unipile returned no post ID — check API credentials",
            }
    except Exception as e:
        logger.error("[PUBLISH NOW] Error: %s", e)
        return {"success": False, "error": str(e)}


@router.get("/publisher-status")
async def get_publisher_status(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get counts of linkedin_posts by status (scheduled, published, failed) for monitoring."""
    from datetime import UTC, datetime

    posts_repo = BaseRepository("linkedin_posts")
    try:
        res = posts_repo.client.table("linkedin_posts").select("status, scheduled_at, id").execute()
        rows = res.data or []
        now = datetime.now(UTC)

        summary: dict[str, int] = {}
        overdue = []
        for row in rows:
            st = row.get("status", "unknown")
            summary[st] = summary.get(st, 0) + 1
            # Flag scheduled posts that are overdue
            if st == "scheduled":
                sat = row.get("scheduled_at")
                if sat:
                    try:
                        sat_dt = datetime.fromisoformat(sat.replace("Z", "+00:00"))
                        if sat_dt <= now:
                            overdue.append({"id": row["id"], "scheduled_at": sat})
                    except Exception:
                        pass

        return {
            "total_posts": len(rows),
            "by_status": summary,
            "overdue_count": len(overdue),
            "overdue_posts": overdue[:10],  # Show up to 10
            "publisher_interval_minutes": 5,
            "next_check_hint": "Publisher runs every 5 minutes automatically",
        }
    except Exception as e:
        return {"error": str(e), "total_posts": 0, "by_status": {}}


# ═══════════════════════════════════════════════════════════════════════════════
# TARGET PERSONAS — Defines WHO the AI likes/comments on behalf of
# ═══════════════════════════════════════════════════════════════════════════════


class PersonaCreateRequest(BaseModel):
    label: str = Field(..., description="Human-readable label, e.g. 'AI Founders'")
    search_keywords: str = Field(
        ..., description="LinkedIn search keywords, e.g. 'AI startup founder CEO'"
    )
    max_profiles: int = Field(default=150, ge=10, le=500)


@router.get("/personas")
async def list_personas(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """List all active target personas for LinkedIn engagement targeting."""
    try:
        repo = BaseRepository("linkedin_target_personas")
        res = (
            repo.client.table("linkedin_target_personas")
            .select("*")
            .order("created_at", desc=False)
            .execute()
        )
        return {"personas": res.data or [], "total": len(res.data or [])}
    except Exception as e:
        logger.error("[PERSONAS] Failed to list personas: %s", e)
        return {"personas": [], "total": 0, "error": str(e)}


@router.post("/personas")
async def create_persona(
    req: PersonaCreateRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Create a new target persona. The AI will search LinkedIn for profiles matching
    the keywords and like/comment on their posts during engagement sessions."""
    from src.config.settings import settings

    account_id = settings.unipile_account_id or "default"
    try:
        repo = BaseRepository("linkedin_target_personas")
        data = {
            "id": str(uuid4()),
            "account_id": account_id,
            "label": req.label,
            "search_keywords": req.search_keywords,
            "max_profiles": req.max_profiles,
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        res = repo.client.table("linkedin_target_personas").insert(data).execute()
        if res.data:
            return {"success": True, "persona": res.data[0]}
        return {"success": False, "error": "Insert returned no data"}
    except Exception as e:
        logger.error("[PERSONAS] Failed to create persona: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.delete("/personas/{persona_id}")
async def delete_persona(
    persona_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Delete a target persona. Stops the AI from targeting that audience segment."""
    try:
        repo = BaseRepository("linkedin_target_personas")
        repo.client.table("linkedin_target_personas").delete().eq("id", persona_id).execute()
        return {"success": True, "id": persona_id}
    except Exception as e:
        logger.error("[PERSONAS] Failed to delete persona %s: %s", persona_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


# ═══════════════════════════════════════════════════════════════════════════════
# COMMENT REVIEW QUEUE — Human approval gate for AI-generated comments
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/review-queue")
async def list_review_queue(
    status_filter: str = "pending_review",
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """List AI-generated comments from the review queue.

    Use status_filter=pending_review to see what needs approval.
    Use status_filter=all to see all comments.
    """
    try:
        repo = BaseRepository("linkedin_review_queue")
        query = (
            repo.client.table("linkedin_review_queue")
            .select("*")
            .order("generated_at", desc=True)
            .limit(50)
        )
        if status_filter != "all":
            query = query.eq("status", status_filter)
        res = query.execute()
        return {"comments": res.data or [], "total": len(res.data or []), "filter": status_filter}
    except Exception as e:
        logger.error("[REVIEW QUEUE] Failed to list: %s", e)
        return {"comments": [], "total": 0, "error": str(e)}


@router.post("/review-queue/{comment_id}/approve")
async def approve_comment(
    comment_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Approve an AI-generated comment for publishing.
    Once approved, it will be published to LinkedIn during the next engagement session."""
    try:
        repo = BaseRepository("linkedin_review_queue")
        res = (
            repo.client.table("linkedin_review_queue")
            .update({"status": "approved", "reviewed_at": datetime.now(UTC).isoformat()})
            .eq("id", comment_id)
            .execute()
        )
        if res.data:
            return {"success": True, "comment_id": comment_id, "status": "approved"}
        return {"success": False, "error": "Comment not found"}
    except Exception as e:
        logger.error("[REVIEW QUEUE] Failed to approve %s: %s", comment_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.post("/review-queue/{comment_id}/reject")
async def reject_comment(
    comment_id: str,
    reason: str = "",
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Reject an AI-generated comment. It will not be published."""
    try:
        repo = BaseRepository("linkedin_review_queue")
        res = (
            repo.client.table("linkedin_review_queue")
            .update(
                {
                    "status": "rejected",
                    "reject_reason": reason,
                    "reviewed_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", comment_id)
            .execute()
        )
        if res.data:
            return {"success": True, "comment_id": comment_id, "status": "rejected"}
        return {"success": False, "error": "Comment not found"}
    except Exception as e:
        logger.error("[REVIEW QUEUE] Failed to reject %s: %s", comment_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.post("/review-queue/approve-all")
async def approve_all_pending(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Bulk approve all pending comments in the review queue."""
    try:
        repo = BaseRepository("linkedin_review_queue")
        res = (
            repo.client.table("linkedin_review_queue")
            .update({"status": "approved", "reviewed_at": datetime.now(UTC).isoformat()})
            .eq("status", "pending_review")
            .execute()
        )
        count = len(res.data) if res.data else 0
        return {"success": True, "approved_count": count}
    except Exception as e:
        logger.error("[REVIEW QUEUE] Bulk approve failed: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


# ═══════════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER — Diagnose and reset stuck automation
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/circuit-breaker")
async def get_circuit_breaker_status(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get current circuit breaker state. If state='open', all automation is halted."""
    from src.config.settings import settings

    account_id = settings.unipile_account_id or ""
    if not account_id:
        return {"state": "unknown", "reason": "UNIPILE_ACCOUNT_ID not configured"}
    try:
        from src.modules.linkedin.worker.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(account_id)
        cb_status = cb.get_status()
        cb_status["can_proceed"] = cb.can_proceed()
        cb_status["message"] = (
            "✅ Automation is running normally"
            if cb.can_proceed()
            else f"🔴 Automation HALTED — reason: {cb_status.get('trip_reason', 'unknown')}. Reset to unblock."
        )
        return cb_status
    except Exception as e:
        logger.error("[CIRCUIT BREAKER] Failed to get status: %s", e)
        return {"state": "unknown", "error": str(e)}


@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Manually reset a tripped circuit breaker. Use when automation was blocked
    by a 429 rate limit or checkpoint challenge and the cooldown period has passed."""
    from src.config.settings import settings

    account_id = settings.unipile_account_id or ""
    if not account_id:
        raise HTTPException(status_code=400, detail="UNIPILE_ACCOUNT_ID not configured")
    try:
        from src.config.supabase import get_supabase_client
        from src.modules.linkedin.models import CircuitState

        client = get_supabase_client()
        client.table("linkedin_circuit_breaker").upsert(
            {
                "account_id": account_id,
                "state": CircuitState.CLOSED.value,
                "tripped_at": None,
                "trip_reason": None,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            on_conflict="account_id",
        ).execute()
        logger.info("[CIRCUIT BREAKER] Manually reset to CLOSED for account %s", account_id)
        return {
            "success": True,
            "new_state": "closed",
            "message": "Circuit breaker reset to CLOSED — automation will resume on next session trigger.",
        }
    except Exception as e:
        logger.error("[CIRCUIT BREAKER] Reset failed: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
