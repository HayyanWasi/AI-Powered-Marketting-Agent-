from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.api.v1.linkedin import _resolve_brand_publishing_account
from src.config.settings import settings
from src.config.supabase import get_supabase_client
from src.gateways.unipile_gateway import get_unipile_gateway
from src.modules.linkedin.account_resolver import resolve_brand_linkedin_account
from src.modules.linkedin.models import (
    EngagementActionType,
    EngagementLogStatus,
    PostStatus,
    ReviewStatus,
)
from src.modules.linkedin.worker.action_ledger import ActionLedger
from src.modules.linkedin.worker.post_publisher import execute_post_publish
from src.modules.linkedin.worker.scheduler import trigger_immediate_engagement_run
from src.repositories.base import BaseRepository
from src.services.campaign_service import CampaignService
from src.utils.sanitizer import sanitize_error_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/autopilot", tags=["Autopilot Control Room"])


async def _resolve_user_brand(
    user_id: str, company_profile_id: str | None = None
) -> dict[str, Any]:
    """Verify and retrieve brand profile owned by user."""
    client = get_supabase_client()
    query = client.table("company_profiles").select("*").eq("user_id", user_id)
    if company_profile_id:
        query = query.eq("id", str(company_profile_id))
    res = query.order("created_at", desc=False).limit(1).execute()
    brands = res.data or []
    if not brands:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found or access denied.",
        )
    return brands[0]


class AutopilotSettingsModel(BaseModel):
    """Brand-scoped engagement automation settings model."""

    company_profile_id: str | None = None
    linkedin_account_id: str | None = None
    connected_account: dict[str, Any] | None = None
    engagement_enabled: bool = False
    auto_like_enabled: bool = False
    auto_comment_generation_enabled: bool = False
    auto_connect_enabled: bool = False
    likes_per_day: int = Field(default=15, ge=0, le=100)
    comments_per_day: int = Field(default=5, ge=0, le=50)
    invites_per_day: int = Field(default=10, ge=0, le=40)
    connection_note_template: str = ""
    timezone: str = "UTC"

    # Backward compatibility with legacy frontend
    daily_connections: int = 10
    daily_likes: int = 15
    daily_comments: int = 5
    master_active: bool = False
    post_time_slot: str = "10:00 AM"
    video_time_slot: str = "04:00 PM"


class AutopilotSettingsUpdateRequest(BaseModel):
    company_profile_id: str | None = None
    engagement_enabled: bool | None = None
    auto_like_enabled: bool | None = None
    auto_comment_generation_enabled: bool | None = None
    auto_connect_enabled: bool | None = None
    likes_per_day: int | None = Field(default=None, ge=0, le=100)
    comments_per_day: int | None = Field(default=None, ge=0, le=50)
    invites_per_day: int | None = Field(default=None, ge=0, le=40)
    connection_note_template: str | None = None
    timezone: str | None = None

    # Backward compatibility fields
    daily_connections: int | None = Field(default=None, ge=1, le=40)
    daily_likes: int | None = Field(default=None, ge=1, le=100)
    daily_comments: int | None = Field(default=None, ge=1, le=50)
    master_active: bool | None = None
    post_time_slot: str | None = None
    video_time_slot: str | None = None


class ToggleRequest(BaseModel):
    active: bool
    company_profile_id: str | None = None


_legacy_settings_store: dict[str, dict[str, Any]] = {}


def _get_user_settings(user_id: str) -> dict[str, Any]:
    """Compatibility helper for legacy test suite."""
    if user_id not in _legacy_settings_store:
        _legacy_settings_store[user_id] = {
            "daily_connections": 25,
            "daily_likes": 40,
            "daily_comments": 15,
            "master_active": True,
            "post_time_slot": "10:00 AM",
            "video_time_slot": "04:00 PM",
        }
    return _legacy_settings_store[user_id]


def _format_settings_response(
    row: dict[str, Any],
    brand_id: str,
    account: dict[str, Any] | None = None,
) -> dict[str, Any]:
    likes = row.get("likes_per_day", 15)
    comments = row.get("comments_per_day", 5)
    invites = row.get("invites_per_day", 10)
    active = row.get("engagement_enabled", False)
    acc_id = str(account["id"]) if account else row.get("linkedin_account_id")
    connected_data = (
        {
            "id": str(account["id"]),
            "user_id": str(account.get("user_id", "")),
            "account_name": account.get("account_name"),
            "account_email": account.get("account_email"),
            "provider": account.get("provider", "LINKEDIN"),
            "status": account.get("status", "connected"),
            "unipile_account_id": account.get("unipile_account_id"),
        }
        if account and account.get("status") == "connected"
        else None
    )
    return {
        "id": row.get("id"),
        "company_profile_id": brand_id,
        "linkedin_account_id": acc_id,
        "connected_account": connected_data,
        "engagement_enabled": active,
        "auto_like_enabled": row.get("auto_like_enabled", False),
        "auto_comment_generation_enabled": row.get("auto_comment_generation_enabled", False),
        "auto_connect_enabled": row.get("auto_connect_enabled", False),
        "likes_per_day": likes,
        "comments_per_day": comments,
        "invites_per_day": invites,
        "connection_note_template": row.get("connection_note_template", ""),
        "timezone": row.get("timezone", "UTC"),
        # Legacy mapping
        "daily_connections": invites,
        "daily_likes": likes,
        "daily_comments": comments,
        "master_active": active,
        "post_time_slot": "10:00 AM",
        "video_time_slot": "04:00 PM",
    }


@router.get("/settings", response_model=AutopilotSettingsModel)
async def get_settings(
    company_profile_id: str | None = None,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get persistent engagement automation settings scoped to the user's brand."""
    brand = await _resolve_user_brand(str(user.id), company_profile_id)
    brand_id = str(brand["id"])
    client = get_supabase_client()

    default_acc_id = brand.get("default_linkedin_account_id")
    account, _ = await resolve_brand_linkedin_account(brand, str(user.id), client=client)

    try:
        res = (
            client.table("linkedin_engagement_settings")
            .select("*")
            .eq("company_profile_id", brand_id)
            .limit(1)
            .execute()
        )
        if res.data:
            row = res.data[0]
            if default_acc_id and row.get("linkedin_account_id") != default_acc_id:
                with contextlib.suppress(Exception):
                    client.table("linkedin_engagement_settings").update(
                        {"linkedin_account_id": default_acc_id}
                    ).eq("id", row["id"]).execute()
                row["linkedin_account_id"] = default_acc_id
            return _format_settings_response(row, brand_id, account)

        # Lazy initialization of default settings for brand
        default_data = {
            "user_id": str(user.id),
            "company_profile_id": brand_id,
            "linkedin_account_id": default_acc_id,
            "engagement_enabled": False,
            "auto_like_enabled": False,
            "auto_comment_generation_enabled": False,
            "auto_connect_enabled": False,
            "likes_per_day": 15,
            "comments_per_day": 5,
            "invites_per_day": 10,
            "connection_note_template": "",
            "timezone": "UTC",
        }
        ins_res = client.table("linkedin_engagement_settings").insert(default_data).execute()
        row = ins_res.data[0] if ins_res.data else default_data
        return _format_settings_response(row, brand_id, account)
    except Exception as e:
        logger.warning("Error fetching settings for brand %s (%s); returning defaults", brand_id, e)
        return _format_settings_response({}, brand_id, account)


@router.put("/settings", response_model=AutopilotSettingsModel)
@router.post("/settings", response_model=AutopilotSettingsModel)
async def update_settings(
    payload: AutopilotSettingsUpdateRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Persist brand engagement limits and toggles to PostgreSQL."""
    brand = await _resolve_user_brand(str(user.id), payload.company_profile_id)
    brand_id = str(brand["id"])
    client = get_supabase_client()

    update_fields: dict[str, Any] = {
        "updated_at": datetime.now(UTC).isoformat(),
    }

    # Map new fields
    if payload.engagement_enabled is not None:
        update_fields["engagement_enabled"] = payload.engagement_enabled
    elif payload.master_active is not None:
        update_fields["engagement_enabled"] = payload.master_active

    if payload.auto_like_enabled is not None:
        update_fields["auto_like_enabled"] = payload.auto_like_enabled
    if payload.auto_comment_generation_enabled is not None:
        update_fields["auto_comment_generation_enabled"] = payload.auto_comment_generation_enabled
    if payload.auto_connect_enabled is not None:
        update_fields["auto_connect_enabled"] = payload.auto_connect_enabled

    if payload.likes_per_day is not None:
        update_fields["likes_per_day"] = payload.likes_per_day
    elif payload.daily_likes is not None:
        update_fields["likes_per_day"] = payload.daily_likes

    if payload.comments_per_day is not None:
        update_fields["comments_per_day"] = payload.comments_per_day
    elif payload.daily_comments is not None:
        update_fields["comments_per_day"] = payload.daily_comments

    if payload.invites_per_day is not None:
        update_fields["invites_per_day"] = payload.invites_per_day
    elif payload.daily_connections is not None:
        update_fields["invites_per_day"] = payload.daily_connections

    if payload.connection_note_template is not None:
        update_fields["connection_note_template"] = payload.connection_note_template
    if payload.timezone is not None:
        update_fields["timezone"] = payload.timezone

    if brand.get("default_linkedin_account_id"):
        update_fields["linkedin_account_id"] = brand.get("default_linkedin_account_id")

    try:
        # Check if settings row exists
        chk = (
            client.table("linkedin_engagement_settings")
            .select("id, engagement_enabled")
            .eq("company_profile_id", brand_id)
            .limit(1)
            .execute()
        )
        was_active = bool(chk.data[0].get("engagement_enabled", False)) if chk.data else False

        if chk.data:
            res = (
                client.table("linkedin_engagement_settings")
                .update(update_fields)
                .eq("company_profile_id", brand_id)
                .execute()
            )
            row = res.data[0] if res.data else update_fields
        else:
            insert_data = {
                "user_id": str(user.id),
                "company_profile_id": brand_id,
                **update_fields,
            }
            res = client.table("linkedin_engagement_settings").insert(insert_data).execute()
            row = res.data[0] if res.data else insert_data

        is_now_active = bool(row.get("engagement_enabled", False))
        if not was_active and is_now_active:
            trigger_immediate_engagement_run()

        account, _ = await resolve_brand_linkedin_account(brand, str(user.id), client=client)
        logger.info("[ENGAGEMENT SETTINGS] Updated settings for brand %s: %s", brand_id, row)
        return _format_settings_response(row, brand_id, account)
    except Exception as e:
        logger.error("[ENGAGEMENT SETTINGS] Update failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save engagement settings: {e}",
        ) from e


@router.post("/toggle")
async def toggle_autopilot(
    req: ToggleRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Toggle master engagement automation state for the brand."""
    brand = await _resolve_user_brand(str(user.id), req.company_profile_id)
    brand_id = str(brand["id"])
    client = get_supabase_client()

    try:
        chk = (
            client.table("linkedin_engagement_settings")
            .select("id, engagement_enabled")
            .eq("company_profile_id", brand_id)
            .limit(1)
            .execute()
        )
        was_active = bool(chk.data[0].get("engagement_enabled", False)) if chk.data else False

        if chk.data:
            client.table("linkedin_engagement_settings").update(
                {
                    "engagement_enabled": req.active,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            ).eq("company_profile_id", brand_id).execute()
        else:
            client.table("linkedin_engagement_settings").insert(
                {
                    "user_id": str(user.id),
                    "company_profile_id": brand_id,
                    "linkedin_account_id": brand.get("default_linkedin_account_id"),
                    "engagement_enabled": req.active,
                }
            ).execute()

        # If transitioning from OFF -> ON, trigger immediate engagement run
        if not was_active and req.active:
            trigger_immediate_engagement_run()

        logger.info("[AUTOPILOT TOGGLE] Brand %s automation toggled to %s", brand_id, req.active)
        return {"status": "success", "master_active": req.active, "company_profile_id": brand_id}
    except Exception as e:
        logger.error("[AUTOPILOT TOGGLE] Toggle failed for brand %s: %s", brand_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/tracker")
async def get_tracker_data(
    company_profile_id: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Aggregated status for Live Campaign Tracking & Progress scoped to authenticated user brand."""
    brand = await _resolve_user_brand(str(user.id), company_profile_id)
    brand_id = str(brand["id"])
    client = get_supabase_client()

    # Load persistent brand settings
    brand_settings: dict[str, Any] = {}
    try:
        set_res = (
            client.table("linkedin_engagement_settings")
            .select("*")
            .eq("company_profile_id", brand_id)
            .limit(1)
            .execute()
        )
        if set_res.data:
            brand_settings = set_res.data[0]
    except Exception as e:
        logger.warning("[AUTOPILOT TRACKER] Could not read engagement settings: %s", e)

    # 1. Fetch campaigns from DB owned by this user
    campaigns_repo = BaseRepository("campaigns")
    posts_repo = BaseRepository("linkedin_posts")

    running_campaigns = []
    upcoming_queue = []
    owned_campaign_ids: list[str] = []

    try:
        camp_res = (
            campaigns_repo.client.table("campaigns")
            .select("*")
            .eq("organization_id", user.id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        if camp_res.data:
            for c in camp_res.data:
                c_name = c.get("name") or "Unnamed Campaign"
                c_status = (c.get("state") or c.get("status") or "ACTIVE").upper()
                c_id = c.get("id")
                if c_id:
                    owned_campaign_ids.append(c_id)
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

    # 2. Fetch real scheduled posts for campaigns owned by this user.
    try:
        if not owned_campaign_ids:
            raise LookupError("No owned campaigns")
        posts_res = (
            posts_repo.client.table("linkedin_posts")
            .select("*")
            .in_("campaign_id", owned_campaign_ids)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        if posts_res.data:
            for p in posts_res.data:
                hook = p.get("hook") or p.get("full_content") or "LinkedIn Post"
                clean_hook = hook.strip().replace("\n", " ")
                if len(clean_hook) > 65:
                    clean_hook = clean_hook[:62] + "..."

                p_status = (p.get("status") or "pending").lower()
                status = "ready" if p_status in ("ready", "published", "scheduled") else "pending"

                upcoming_queue.append(
                    {
                        "id": p.get("id"),
                        "type": "video" if p.get("media_type") == "video" else "post",
                        "title": clean_hook,
                        "scheduled_time": p.get("scheduled_at") or "Not scheduled",
                        "status": status,
                    }
                )
    except LookupError:
        pass
    except Exception as e:
        logger.warning("[AUTOPILOT TRACKER] Could not read posts: %s", e)

    action_counts: dict[str, int] = {}
    default_acc_id = brand.get("default_linkedin_account_id")
    if default_acc_id:
        tz_name = brand_settings.get("timezone") or settings.linkedin_timezone
        try:
            action_counts = await ActionLedger().get_daily_summary(str(default_acc_id), tz_name)
        except Exception as e:
            logger.warning(
                "[AUTOPILOT TRACKER] Could not read action counts for account %s: %s",
                default_acc_id,
                e,
            )

    return {
        "master_active": brand_settings.get("engagement_enabled", False),
        "company_profile_id": brand_id,
        "daily_progress": {
            "connections_sent": action_counts.get("invite", 0),
            "connections_max": brand_settings.get("invites_per_day", 10),
            "likes_given": action_counts.get("like", 0),
            "likes_max": brand_settings.get("likes_per_day", 15),
            "comments_posted": action_counts.get("comment", 0),
            "comments_max": brand_settings.get("comments_per_day", 5),
        },
        "upcoming_queue": upcoming_queue,
        "running_campaigns": running_campaigns,
    }


@router.delete("/queue/{job_id}")
async def delete_queue_job(
    job_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Delete or cancel a scheduled job from the upcoming queue, verifying tenant ownership."""
    posts_repo = BaseRepository("linkedin_posts")
    campaigns_repo = BaseRepository("campaigns")

    try:
        # 1. Resolve post and its campaign_id
        post_res = (
            posts_repo.client.table("linkedin_posts")
            .select("id, campaign_id")
            .eq("id", job_id)
            .execute()
        )
        if not post_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Queue item not found",
            )

        post = post_res.data[0]
        campaign_id = post.get("campaign_id")
        if not campaign_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Queue item not found",
            )

        # 2. Verify campaign ownership by authenticated user
        camp_res = (
            campaigns_repo.client.table("campaigns")
            .select("id, organization_id")
            .eq("id", str(campaign_id))
            .execute()
        )
        if not camp_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Queue item not found",
            )

        campaign = camp_res.data[0]
        if str(campaign.get("organization_id")) != str(user.id):
            # Return 404 instead of 403 to prevent existence leakage
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Queue item not found",
            )

        # 3. Ownership confirmed; delete the queued post
        res = posts_repo.client.table("linkedin_posts").delete().eq("id", job_id).execute()
        deleted_from_db = bool(res.data)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[AUTOPILOT] Could not delete from linkedin_posts: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete queue item: {e}",
        ) from e

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
    """Immediately publish a specific draft post to LinkedIn (Phase D Safe Publish Now).

    Requirements:
    1. Authenticated user owns post -> campaign -> brand.
    2. Post must be in 'draft' status. 'scheduled', 'publishing', 'published',
       'failed', and 'needs_review' return 409 Conflict.
    3. Content must not be empty (422).
    4. Publishing account resolved deterministically from brand default account (409 if missing/disconnected).
    5. Atomic claim (draft -> publishing) BEFORE any external dispatch. If 0 rows updated -> 409 Conflict.
    6. External dispatch via execute_post_publish with provider failure classification.
    """
    try:
        post_uuid = UUID(post_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found.",
        ) from None

    posts_repo = BaseRepository("linkedin_posts")

    # 1. Fetch post
    try:
        res = (
            posts_repo.client.table("linkedin_posts")
            .select("*")
            .eq("id", str(post_uuid))
            .limit(1)
            .execute()
        )
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post {post_id} not found.",
            )
        post = res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[PUBLISH NOW] Failed to load post %s: %s", post_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load post: {e}",
        ) from e

    # 2. Ownership verification: post -> campaign -> brand
    campaign_id = post.get("campaign_id")
    if not campaign_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} has no associated campaign.",
        )

    try:
        campaign = await CampaignService().get_campaign(UUID(campaign_id), UUID(user.id))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found or access denied.",
        ) from None

    # 3. Status precondition guards (draft only)
    current_status = post.get("status")
    if current_status != PostStatus.DRAFT.value:
        if current_status == PostStatus.SCHEDULED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Scheduled posts cannot be published directly. Cancel the schedule first to publish immediately.",
            )
        elif current_status == PostStatus.PUBLISHING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Post is currently being published.",
            )
        elif current_status == PostStatus.PUBLISHED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Post is already published.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Post cannot be published now from status '{current_status}'.",
            )

    # 4. Content check
    full_content = (post.get("full_content") or "").strip()
    if not full_content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Post content cannot be empty.",
        )

    # 5. Resolve brand default LinkedIn account
    account, reason = await _resolve_brand_publishing_account(
        str(user.id), campaign, action_verb="publishing"
    )
    if not account or reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=reason or "No connected LinkedIn account is configured for this brand.",
        )

    account_unipile_id = account.get("unipile_account_id")
    if not account_unipile_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The brand's LinkedIn account has no Unipile identifier.",
        )

    # 6. Atomic claim: draft -> publishing BEFORE any external call
    try:
        claim_res = (
            posts_repo.client.table("linkedin_posts")
            .update(
                {
                    "status": PostStatus.PUBLISHING.value,
                    "publishing_started_at": datetime.now(UTC).isoformat(),
                    "linkedin_account_id": account_unipile_id,
                }
            )
            .eq("id", str(post_uuid))
            .eq("status", PostStatus.DRAFT.value)
            .execute()
        )
    except Exception as e:
        logger.error("[PUBLISH NOW] Atomic claim query failed for post %s: %s", post_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to claim post for publishing: {e}",
        ) from e

    if not claim_res.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Post could not be claimed for publishing (status may have changed concurrently).",
        )

    # 7. External dispatch and failure classification via shared publisher logic
    gateway = get_unipile_gateway()
    result = await execute_post_publish(
        posts_repo,
        gateway,
        str(post_uuid),
        account_unipile_id,
        full_content,
        media_url=post.get("media_url"),
    )

    if result.get("status") == PostStatus.PUBLISHED.value:
        return {
            "success": True,
            "status": "published",
            "post_id": str(post_uuid),
            "unipile_post_id": result.get("unipile_post_id"),
            "published_at": result.get("published_at"),
            "linkedin_account_id": account_unipile_id,
            "post": result.get("post"),
            "message": "Post published to LinkedIn!",
        }
    elif result.get("status") == PostStatus.NEEDS_REVIEW.value:
        return {
            "success": False,
            "status": "needs_review",
            "post_id": str(post_uuid),
            "unipile_post_id": result.get("unipile_post_id"),
            "error": result.get("error") or "Ambiguous publish state; post moved to needs_review.",
        }
    else:
        return {
            "success": False,
            "status": "failed",
            "post_id": str(post_uuid),
            "error": result.get("error") or "Publishing failed.",
        }


@router.get("/publisher-status")
async def get_publisher_status(
    company_profile_id: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get counts of linkedin_posts by status scoped to authenticated user and brand."""
    from datetime import UTC, datetime

    campaigns_repo = BaseRepository("campaigns")
    posts_repo = BaseRepository("linkedin_posts")
    try:
        camp_query = (
            campaigns_repo.client.table("campaigns")
            .select("id")
            .eq("organization_id", str(user.id))
        )
        if isinstance(company_profile_id, str) and company_profile_id.strip():
            brand = await _resolve_user_brand(str(user.id), company_profile_id.strip())
            camp_query = camp_query.eq("company_profile_id", str(brand["id"]))
        camp_res = camp_query.execute()
        owned_campaign_ids = [c["id"] for c in (camp_res.data or []) if c.get("id")]

        if not owned_campaign_ids:
            return {
                "total_posts": 0,
                "by_status": {},
                "overdue_count": 0,
                "overdue_posts": [],
                "publisher_interval_minutes": 5,
                "next_check_hint": "Publisher runs every 5 minutes automatically",
            }

        res = (
            posts_repo.client.table("linkedin_posts")
            .select("status, scheduled_at, id")
            .in_("campaign_id", owned_campaign_ids)
            .execute()
        )
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
# TARGET PERSONAS — Defines WHO the AI likes/comments on behalf of (Brand Scoped)
# ═══════════════════════════════════════════════════════════════════════════════


class PersonaCreateRequest(BaseModel):
    company_profile_id: str | None = Field(default=None, description="Target brand profile ID")
    label: str = Field(..., description="Human-readable label, e.g. 'AI Founders'")
    search_keywords: str = Field(
        ..., description="LinkedIn search keywords, e.g. 'AI startup founder CEO'"
    )
    max_profiles: int = Field(default=150, ge=10, le=500)


class PersonaUpdateRequest(BaseModel):
    label: str | None = None
    search_keywords: str | None = None
    max_profiles: int | None = Field(default=None, ge=10, le=500)
    is_active: bool | None = None


@router.get("/personas")
async def list_personas(
    company_profile_id: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """List target personas for the active brand."""
    brand = await _resolve_user_brand(str(user.id), company_profile_id)
    brand_id = str(brand["id"])
    try:
        repo = BaseRepository("linkedin_target_personas")
        res = (
            repo.client.table("linkedin_target_personas")
            .select("*")
            .eq("company_profile_id", brand_id)
            .order("created_at", desc=False)
            .execute()
        )
        return {
            "personas": res.data or [],
            "total": len(res.data or []),
            "company_profile_id": brand_id,
        }
    except Exception as e:
        logger.error("[PERSONAS] Failed to list personas for brand %s: %s", brand_id, e)
        return {"personas": [], "total": 0, "error": str(e), "company_profile_id": brand_id}


@router.post("/personas")
async def create_persona(
    req: PersonaCreateRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Create a new target persona scoped to the authenticated user's brand."""
    brand = await _resolve_user_brand(str(user.id), req.company_profile_id)
    brand_id = str(brand["id"])

    try:
        repo = BaseRepository("linkedin_target_personas")
        data = {
            "id": str(uuid4()),
            "user_id": str(user.id),
            "company_profile_id": brand_id,
            "label": req.label.strip(),
            "search_keywords": req.search_keywords.strip(),
            "max_profiles": req.max_profiles,
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        res = repo.client.table("linkedin_target_personas").insert(data).execute()
        if res.data:
            return {"success": True, "persona": res.data[0]}
        return {"success": False, "error": "Insert returned no data"}
    except Exception as e:
        logger.error("[PERSONAS] Failed to create persona for brand %s: %s", brand_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.put("/personas/{persona_id}")
async def update_persona(
    persona_id: str,
    req: PersonaUpdateRequest,
    company_profile_id: str = Query(..., description="Active brand profile ID"),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Update a target persona owned by the authenticated user within the specified brand."""
    # 1. Verify user owns the requested brand context
    brand = await _resolve_user_brand(str(user.id), company_profile_id)
    brand_id = str(brand["id"])

    repo = BaseRepository("linkedin_target_personas")
    try:
        # 2. Fetch persona
        chk = (
            repo.client.table("linkedin_target_personas").select("*").eq("id", persona_id).execute()
        )
        if not chk.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        persona = chk.data[0]

        # 3. Verify user ownership (404 if owned by another user to prevent existence leakage)
        if persona.get("user_id") and str(persona.get("user_id")) != str(user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")

        # 4. Verify brand match (403 if user owns persona but under a different brand)
        if str(persona.get("company_profile_id")) != brand_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Persona does not belong to the specified brand profile",
            )

        update_data: dict[str, Any] = {}
        if req.label is not None:
            update_data["label"] = req.label.strip()
        if req.search_keywords is not None:
            update_data["search_keywords"] = req.search_keywords.strip()
        if req.max_profiles is not None:
            update_data["max_profiles"] = req.max_profiles
        if req.is_active is not None:
            update_data["is_active"] = req.is_active

        if not update_data:
            return {"success": True, "persona": persona}

        res = (
            repo.client.table("linkedin_target_personas")
            .update(update_data)
            .eq("id", persona_id)
            .execute()
        )
        return {"success": True, "persona": res.data[0] if res.data else persona}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[PERSONAS] Failed to update persona %s: %s", persona_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.delete("/personas/{persona_id}")
async def delete_persona(
    persona_id: str,
    company_profile_id: str = Query(..., description="Active brand profile ID"),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Delete a target persona owned by the authenticated user within the specified brand."""
    # 1. Verify user owns the requested brand context
    brand = await _resolve_user_brand(str(user.id), company_profile_id)
    brand_id = str(brand["id"])

    repo = BaseRepository("linkedin_target_personas")
    try:
        # 2. Fetch persona
        chk = (
            repo.client.table("linkedin_target_personas").select("*").eq("id", persona_id).execute()
        )
        if not chk.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        persona = chk.data[0]

        # 3. Verify user ownership (404 if owned by another user to prevent existence leakage)
        if persona.get("user_id") and str(persona.get("user_id")) != str(user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")

        # 4. Verify brand match (403 if user owns persona but under a different brand)
        if str(persona.get("company_profile_id")) != brand_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Persona does not belong to the specified brand profile",
            )

        repo.client.table("linkedin_target_personas").delete().eq("id", persona_id).execute()
        return {"success": True, "id": persona_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[PERSONAS] Failed to delete persona %s: %s", persona_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


# ═══════════════════════════════════════════════════════════════════════════════
# COMMENT REVIEW QUEUE — Human approval gate for AI-generated comments
# ═══════════════════════════════════════════════════════════════════════════════


class ApproveCommentRequest(BaseModel):
    comment_text: str | None = Field(default=None, description="Optional edited comment text")


class RejectCommentRequest(BaseModel):
    reason: str | None = Field(default="", description="Rejection reason")


@router.get("/review-queue")
@router.get("/review")
async def list_review_queue(
    company_profile_id: str | None = Query(default=None),
    status_filter: str = "pending_review",
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """List AI-generated comments from the review queue for the brand.

    Use status_filter=pending_review to see what needs approval.
    Use status_filter=all to see all comments.
    """
    brand = await _resolve_user_brand(str(user.id), company_profile_id)
    brand_id = str(brand["id"])
    try:
        repo = BaseRepository("linkedin_review_queue")
        query = (
            repo.client.table("linkedin_review_queue")
            .select("*")
            .eq("company_profile_id", brand_id)
            .order("generated_at", desc=True)
            .limit(50)
        )
        if status_filter != "all":
            query = query.eq("status", status_filter)
        res = query.execute()
        return {
            "comments": res.data or [],
            "total": len(res.data or []),
            "filter": status_filter,
            "company_profile_id": brand_id,
        }
    except Exception as e:
        logger.error("[REVIEW QUEUE] Failed to list for brand %s: %s", brand_id, e)
        return {"comments": [], "total": 0, "error": str(e), "company_profile_id": brand_id}


@router.post("/review/{review_id}/approve")
@router.post("/review-queue/{review_id}/approve")
async def approve_comment(
    review_id: str,
    payload: ApproveCommentRequest | None = None,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Crash-safe 3-Phase comment approval and dispatch.

    Phase 1: Atomic state claim:
      - Conditional update `pending_review -> approved`
      - Insert durable claim into `linkedin_engagement_log` (status='claimed')
      - If claim fails or conflicts -> ROLL BACK approval and abort.
    Phase 2: External HTTP call to Unipile (outside DB transaction).
    Phase 3: Finalization:
      - Succeeded: review_queue -> published, log -> succeeded, engaged_posts insert, ledger increment.
      - Timeout / Ambiguous: review_queue -> needs_review, log -> needs_review.
      - Confirmed Failure: review_queue -> failed, log -> failed.
    """
    repo = BaseRepository("linkedin_review_queue")
    client = repo.client

    # 1. Fetch and verify ownership
    try:
        chk = client.table("linkedin_review_queue").select("*").eq("id", review_id).execute()
        if not chk.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found in review queue"
            )
        item = chk.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[REVIEW APPROVE] Fetch failed: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    # Tenancy verification
    if item.get("user_id") and item.get("user_id") != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to approve this comment"
        )

    brand_id = str(item.get("company_profile_id"))
    # Verify user owns the brand
    await _resolve_user_brand(str(user.id), brand_id)

    # Verify linked LinkedIn account
    account_uuid = item.get("linkedin_account_id")
    if not account_uuid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="No LinkedIn account linked to review item"
        )

    acc_res = client.table("linkedin_accounts").select("*").eq("id", account_uuid).execute()
    if not acc_res.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Linked LinkedIn account not found"
        )
    account = acc_res.data[0]
    if account.get("user_id") != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="LinkedIn account does not belong to user"
        )
    if account.get("status") != "connected":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Linked LinkedIn account is disconnected"
        )

    account_unipile_id = account.get("unipile_account_id")
    if not account_unipile_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Missing unipile_account_id for account"
        )

    # Determine final text
    final_text = ""
    if payload and payload.comment_text and payload.comment_text.strip():
        final_text = payload.comment_text.strip()
    else:
        final_text = (item.get("generated_text") or "").strip()

    if not final_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comment text cannot be empty"
        )

    target_post_id = str(item["target_post_id"])
    now_iso = datetime.now(UTC).isoformat()

    # ── PHASE 1: ATOMIC DB STATE CLAIM ──
    # 1. Conditional update review_queue pending_review -> approved
    claim_res = (
        client.table("linkedin_review_queue")
        .update(
            {
                "status": ReviewStatus.APPROVED.value,
                "generated_text": final_text,
                "reviewed_at": now_iso,
            }
        )
        .eq("id", review_id)
        .eq("status", ReviewStatus.PENDING_REVIEW.value)
        .execute()
    )

    if not claim_res.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Comment {review_id} is not in pending_review status (current status: {item.get('status')})",
        )

    # 2. Insert durable claim into linkedin_engagement_log
    log_claim_id = str(uuid4())
    log_insert_data = {
        "id": log_claim_id,
        "user_id": str(user.id),
        "company_profile_id": brand_id,
        "linkedin_account_id": str(account_uuid),
        "action_type": EngagementActionType.COMMENT.value,
        "target_post_id": target_post_id,
        "review_queue_id": review_id,
        "comment_text": final_text,
        "status": EngagementLogStatus.CLAIMED.value,
        "created_at": now_iso,
    }

    try:
        log_res = client.table("linkedin_engagement_log").insert(log_insert_data).execute()
        if not log_res.data:
            raise RuntimeError("Insert returned no data")
        # Link action_log_id on review item
        client.table("linkedin_review_queue").update({"action_log_id": log_claim_id}).eq(
            "id", review_id
        ).execute()
    except Exception as e:
        logger.error(
            "[REVIEW APPROVE] Claim insert into engagement log failed: %s. Rolling back approval.",
            e,
        )
        # Roll back review item to pending_review
        client.table("linkedin_review_queue").update(
            {
                "status": ReviewStatus.PENDING_REVIEW.value,
            }
        ).eq("id", review_id).execute()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Durable engagement claim conflict or failure: {e}",
        ) from e

    logger.info(
        "[REVIEW APPROVE] Phase 1 committed: review %s approved, claim %s created",
        review_id,
        log_claim_id,
    )

    # ── PHASE 2: EXTERNAL CALL (NO DB TRANSACTION OPEN) ──
    gateway = get_unipile_gateway()
    completed_iso = datetime.now(UTC).isoformat()
    provider_result_id = ""
    error_msg = ""
    is_ambiguous = False
    is_success = False

    try:
        resp = await gateway.comment_on_post(
            account_id=account_unipile_id,
            post_id=target_post_id,
            text=final_text,
        )
        if isinstance(resp, dict):
            provider_result_id = str(resp.get("comment_id") or resp.get("id") or "").strip()
        elif isinstance(resp, str):
            provider_result_id = resp.strip()
        else:
            provider_result_id = ""

        if provider_result_id:
            is_success = True
            logger.info(
                "[REVIEW APPROVE] Phase 2 succeeded for review %s: provider_id=%s",
                review_id,
                provider_result_id,
            )
        else:
            # Ambiguous/unknown outcome without reliable provider confirmation => needs_review
            is_ambiguous = True
            error_msg = "Ambiguous dispatch: Provider returned empty or unconfirmed response"
            logger.warning(
                "[REVIEW APPROVE] Phase 2 ambiguous outcome for review %s: %s",
                review_id,
                error_msg,
            )
    except (httpx.TimeoutException, TimeoutError) as exc:
        is_ambiguous = True
        error_msg = f"Timeout during Unipile dispatch: {exc}"
        logger.error("[REVIEW APPROVE] Phase 2 ambiguous timeout for review %s: %s", review_id, exc)
    except httpx.HTTPStatusError as exc:
        if 400 <= exc.response.status_code < 500:
            error_msg = f"Definitive provider rejection (HTTP {exc.response.status_code}): {exc}"
            logger.error(
                "[REVIEW APPROVE] Phase 2 definitive rejection for review %s: %s", review_id, exc
            )
        else:
            is_ambiguous = True
            error_msg = f"Ambiguous provider server error (HTTP {exc.response.status_code}): {exc}"
            logger.error(
                "[REVIEW APPROVE] Phase 2 ambiguous server error for review %s: %s", review_id, exc
            )
    except Exception as exc:
        error_msg = f"Unipile dispatch failure: {exc}"
        logger.error(
            "[REVIEW APPROVE] Phase 2 deterministic failure for review %s: %s", review_id, exc
        )

    # ── PHASE 3: FINALIZATION ──
    if is_success:
        try:
            client.table("linkedin_review_queue").update(
                {
                    "status": ReviewStatus.PUBLISHED.value,
                }
            ).eq("id", review_id).execute()

            client.table("linkedin_engagement_log").update(
                {
                    "status": EngagementLogStatus.SUCCEEDED.value,
                    "provider_result_id": provider_result_id,
                    "completed_at": completed_iso,
                }
            ).eq("id", log_claim_id).execute()

            # Record in engaged posts
            client.table("linkedin_engaged_posts").upsert(
                {
                    "linkedin_account_id": str(account_uuid),
                    "post_id": target_post_id,
                    "action_type": EngagementActionType.COMMENT.value,
                    "engaged_at": completed_iso,
                }
            ).execute()

            # Record in daily ledger
            await ActionLedger().record_action(
                account_id=str(account_uuid),
                action_type=EngagementActionType.COMMENT.value,
            )
        except Exception as finalize_exc:
            logger.error(
                "[REVIEW APPROVE] Finalization error for review %s: %s", review_id, finalize_exc
            )

        return {
            "success": True,
            "status": "published",
            "comment_id": review_id,
            "provider_result_id": provider_result_id,
            "message": "Comment approved and published to LinkedIn.",
        }

    elif is_ambiguous:
        client.table("linkedin_review_queue").update(
            {
                "status": ReviewStatus.NEEDS_REVIEW.value,
            }
        ).eq("id", review_id).execute()

        client.table("linkedin_engagement_log").update(
            {
                "status": EngagementLogStatus.NEEDS_REVIEW.value,
                "error_message": error_msg,
                "completed_at": completed_iso,
            }
        ).eq("id", log_claim_id).execute()

        return {
            "success": False,
            "status": "needs_review",
            "comment_id": review_id,
            "error": error_msg,
        }

    else:
        client.table("linkedin_review_queue").update(
            {
                "status": ReviewStatus.FAILED.value,
            }
        ).eq("id", review_id).execute()

        client.table("linkedin_engagement_log").update(
            {
                "status": EngagementLogStatus.FAILED.value,
                "error_message": error_msg,
                "completed_at": completed_iso,
            }
        ).eq("id", log_claim_id).execute()

        return {
            "success": False,
            "status": "failed",
            "comment_id": review_id,
            "error": error_msg,
        }


@router.post("/review/{review_id}/reject")
@router.post("/review-queue/{review_id}/reject")
async def reject_comment(
    review_id: str,
    payload: RejectCommentRequest | None = None,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Reject an AI-generated comment without dispatching any external call."""
    repo = BaseRepository("linkedin_review_queue")
    client = repo.client
    try:
        chk = client.table("linkedin_review_queue").select("*").eq("id", review_id).execute()
        if not chk.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found in review queue"
            )
        item = chk.data[0]
        if item.get("user_id") and item.get("user_id") != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to reject this comment",
            )

        reason = (payload.reason or "").strip() if payload else ""
        res = (
            client.table("linkedin_review_queue")
            .update(
                {
                    "status": ReviewStatus.REJECTED.value,
                    "reject_reason": reason,
                    "reviewed_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", review_id)
            .eq("status", ReviewStatus.PENDING_REVIEW.value)
            .execute()
        )
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Comment is not in pending_review status (current status: {item.get('status')})",
            )
        return {"success": True, "comment_id": review_id, "status": "rejected"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[REVIEW QUEUE] Failed to reject %s: %s", review_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


# ═══════════════════════════════════════════════════════════════════════════════
# ENGAGEMENT ACTIVITY — Authoritative Event Log History
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/activity")
async def get_engagement_activity(
    company_profile_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Return real authoritative engagement activity events from linkedin_engagement_log."""
    brand = await _resolve_user_brand(str(user.id), company_profile_id)
    brand_id = str(brand["id"])
    client = get_supabase_client()
    try:
        res = (
            client.table("linkedin_engagement_log")
            .select("*")
            .eq("company_profile_id", brand_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {
            "events": res.data or [],
            "total": len(res.data or []),
            "company_profile_id": brand_id,
        }
    except Exception as e:
        logger.error("[ENGAGEMENT ACTIVITY] Failed to fetch activity for brand %s: %s", brand_id, e)
        return {
            "events": [],
            "total": 0,
            "company_profile_id": brand_id,
            "error": str(e),
        }


def _canonical_publishing_timestamp(post: dict[str, Any]) -> str:
    """Resolve canonical timestamp for a publishing post based on status."""
    st = (post.get("status") or "").lower()
    if st == "published" and post.get("published_at"):
        return str(post["published_at"])
    if st == "publishing":
        return str(
            post.get("publishing_started_at")
            or post.get("created_at")
            or datetime.now(UTC).isoformat()
        )
    if st == "scheduled" and post.get("scheduled_at"):
        return str(post["scheduled_at"])
    if st == "draft":
        return str(post.get("created_at") or datetime.now(UTC).isoformat())
    return str(
        post.get("published_at")
        or post.get("publishing_started_at")
        or post.get("created_at")
        or post.get("scheduled_at")
        or datetime.now(UTC).isoformat()
    )


def _canonical_engagement_timestamp(log: dict[str, Any]) -> str:
    """Resolve canonical timestamp for an engagement action log."""
    return str(log.get("completed_at") or log.get("created_at") or datetime.now(UTC).isoformat())


@router.get("/activity/unified")
async def get_unified_activity(
    company_profile_id: str | None = Query(default=None),
    source_type: str = Query(default="all"),
    action_type: str = Query(default="all"),
    filter_status: str | None = Query(default=None, alias="status"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1000),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Unified Activity API returning normalized, tenant-scoped publishing and engagement history.

    Powers /history by consolidating:
    1. Publishing events from linkedin_posts (scoped via campaigns.organization_id == user.id)
    2. Engagement events from linkedin_engagement_log (scoped via user_id == user.id)

    Guarantees:
    - Zero unbounded table scans (exact counts + bounded fetch)
    - Strict multi-tenant isolation
    - Error message credential sanitization
    - Sorted newest first with offset/limit pagination
    """
    # Unpack query defaults if invoked directly in unit tests without FastAPI DI
    source_type = source_type.default if hasattr(source_type, "default") else (source_type or "all")
    action_type = action_type.default if hasattr(action_type, "default") else (action_type or "all")
    company_profile_id = (
        company_profile_id.default if hasattr(company_profile_id, "default") else company_profile_id
    )
    filter_status = filter_status.default if hasattr(filter_status, "default") else filter_status
    start_date = start_date.default if hasattr(start_date, "default") else start_date
    end_date = end_date.default if hasattr(end_date, "default") else end_date
    limit = limit.default if hasattr(limit, "default") else (limit or 50)
    offset = offset.default if hasattr(offset, "default") else (offset or 0)

    # 1. Parameter Validation
    allowed_sources = {"all", "publishing", "engagement"}
    if source_type not in allowed_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source_type '{source_type}'. Allowed: {', '.join(sorted(allowed_sources))}",
        )

    allowed_actions = {"all", "post", "like", "comment", "connection_request"}
    if action_type not in allowed_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action_type '{action_type}'. Allowed: {', '.join(sorted(allowed_actions))}",
        )

    user_id_str = str(user.id)
    client = get_supabase_client()

    # 2. Strict company profile ownership validation if specified
    if company_profile_id:
        await _resolve_user_brand(user_id_str, company_profile_id)

    # 3. Determine sources to fetch
    include_publishing = source_type in ("all", "publishing") and action_type in ("all", "post")
    include_engagement = source_type in ("all", "engagement") and action_type in (
        "all",
        "like",
        "comment",
        "connection_request",
    )

    publishing_total = 0
    raw_posts: list[dict[str, Any]] = []
    camp_map: dict[str, dict[str, Any]] = {}

    fetch_limit = offset + limit

    # 4. Fetch Publishing Data (canonical-aligned status buckets)
    if include_publishing:
        camp_query = (
            client.table("campaigns")
            .select("id, name, company_profile_id")
            .eq("organization_id", user_id_str)
        )
        if company_profile_id:
            camp_query = camp_query.eq("company_profile_id", str(company_profile_id))

        try:
            camp_res = camp_query.execute()
            campaigns = camp_res.data or []
        except Exception as e:
            logger.warning("[UNIFIED ACTIVITY] Failed to query user campaigns: %s", e)
            campaigns = []

        if campaigns:
            camp_map = {str(c["id"]): c for c in campaigns}
            owned_camp_ids = list(camp_map.keys())

            try:
                count_q = (
                    client.table("linkedin_posts")
                    .select("id", count="exact")
                    .in_("campaign_id", owned_camp_ids)
                )
                if filter_status:
                    count_q = count_q.eq("status", filter_status)
                if start_date:
                    count_q = count_q.gte("created_at", start_date)
                if end_date:
                    count_q = count_q.lte("created_at", end_date)
                count_res = count_q.execute()
                publishing_total = count_res.count or 0

                raw_posts_dict: dict[str, dict[str, Any]] = {}

                def _add_posts(posts: list[dict[str, Any]] | None) -> None:
                    if posts:
                        for p in posts:
                            raw_posts_dict[str(p["id"])] = p

                def _make_base_post_q():
                    q = (
                        client.table("linkedin_posts")
                        .select("*")
                        .in_("campaign_id", owned_camp_ids)
                    )
                    if start_date:
                        q = q.gte("created_at", start_date)
                    if end_date:
                        q = q.lte("created_at", end_date)
                    return q

                all_publishing_statuses = [
                    "published",
                    "publishing",
                    "scheduled",
                    "draft",
                    "failed",
                    "needs_review",
                ]
                statuses_to_fetch = [filter_status] if filter_status else all_publishing_statuses

                for st in statuses_to_fetch:
                    if st == "published":
                        res1 = (
                            _make_base_post_q()
                            .eq("status", "published")
                            .not_.is_("published_at", "null")
                            .order("published_at", desc=True)
                            .order("id", desc=True)
                            .limit(fetch_limit)
                            .execute()
                        )
                        _add_posts(res1.data)
                        res2 = (
                            _make_base_post_q()
                            .eq("status", "published")
                            .is_("published_at", "null")
                            .order("created_at", desc=True)
                            .order("id", desc=True)
                            .limit(fetch_limit)
                            .execute()
                        )
                        _add_posts(res2.data)
                    elif st == "publishing":
                        res1 = (
                            _make_base_post_q()
                            .eq("status", "publishing")
                            .not_.is_("publishing_started_at", "null")
                            .order("publishing_started_at", desc=True)
                            .order("id", desc=True)
                            .limit(fetch_limit)
                            .execute()
                        )
                        _add_posts(res1.data)
                        res2 = (
                            _make_base_post_q()
                            .eq("status", "publishing")
                            .is_("publishing_started_at", "null")
                            .order("created_at", desc=True)
                            .order("id", desc=True)
                            .limit(fetch_limit)
                            .execute()
                        )
                        _add_posts(res2.data)
                    elif st == "scheduled":
                        res1 = (
                            _make_base_post_q()
                            .eq("status", "scheduled")
                            .not_.is_("scheduled_at", "null")
                            .order("scheduled_at", desc=True)
                            .order("id", desc=True)
                            .limit(fetch_limit)
                            .execute()
                        )
                        _add_posts(res1.data)
                        res2 = (
                            _make_base_post_q()
                            .eq("status", "scheduled")
                            .is_("scheduled_at", "null")
                            .order("created_at", desc=True)
                            .order("id", desc=True)
                            .limit(fetch_limit)
                            .execute()
                        )
                        _add_posts(res2.data)
                    elif st in ("draft", "failed", "needs_review"):
                        res = (
                            _make_base_post_q()
                            .eq("status", st)
                            .order("created_at", desc=True)
                            .order("id", desc=True)
                            .limit(fetch_limit)
                            .execute()
                        )
                        _add_posts(res.data)
                    else:
                        res = (
                            _make_base_post_q()
                            .eq("status", st)
                            .order("created_at", desc=True)
                            .order("id", desc=True)
                            .limit(fetch_limit)
                            .execute()
                        )
                        _add_posts(res.data)

                if not filter_status:
                    res_other = (
                        _make_base_post_q()
                        .not_.in_("status", all_publishing_statuses)
                        .order("created_at", desc=True)
                        .order("id", desc=True)
                        .limit(fetch_limit)
                        .execute()
                    )
                    _add_posts(res_other.data)

                raw_posts = list(raw_posts_dict.values())
            except Exception as e:
                logger.error("[UNIFIED ACTIVITY] Failed to query publishing posts: %s", e)
                publishing_total = 0
                raw_posts = []

    # 5. Fetch Engagement Data (canonical-aligned status buckets)
    engagement_total = 0
    raw_logs: list[dict[str, Any]] = []

    if include_engagement:
        try:
            eng_count_q = (
                client.table("linkedin_engagement_log")
                .select("id", count="exact")
                .eq("user_id", user_id_str)
            )
            if company_profile_id:
                eng_count_q = eng_count_q.eq("company_profile_id", str(company_profile_id))
            if action_type != "all":
                eng_count_q = eng_count_q.eq("action_type", action_type)
            if filter_status:
                eng_count_q = eng_count_q.eq("status", filter_status)
            if start_date:
                eng_count_q = eng_count_q.gte("created_at", start_date)
            if end_date:
                eng_count_q = eng_count_q.lte("created_at", end_date)
            eng_count_res = eng_count_q.execute()
            engagement_total = eng_count_res.count or 0

            raw_logs_dict: dict[str, dict[str, Any]] = {}

            def _add_logs(logs: list[dict[str, Any]] | None) -> None:
                if logs:
                    for log_item in logs:
                        raw_logs_dict[str(log_item["id"])] = log_item

            def _make_base_eng_q():
                q = client.table("linkedin_engagement_log").select("*").eq("user_id", user_id_str)
                if company_profile_id:
                    q = q.eq("company_profile_id", str(company_profile_id))
                if action_type != "all":
                    q = q.eq("action_type", action_type)
                if filter_status:
                    q = q.eq("status", filter_status)
                if start_date:
                    q = q.gte("created_at", start_date)
                if end_date:
                    q = q.lte("created_at", end_date)
                return q

            # Bucket 1: completed_at not null -> completed_at DESC, id DESC
            res_eng1 = (
                _make_base_eng_q()
                .not_.is_("completed_at", "null")
                .order("completed_at", desc=True)
                .order("id", desc=True)
                .limit(fetch_limit)
                .execute()
            )
            _add_logs(res_eng1.data)

            # Bucket 2: completed_at is null -> created_at DESC, id DESC
            res_eng2 = (
                _make_base_eng_q()
                .is_("completed_at", "null")
                .order("created_at", desc=True)
                .order("id", desc=True)
                .limit(fetch_limit)
                .execute()
            )
            _add_logs(res_eng2.data)

            raw_logs = list(raw_logs_dict.values())
        except Exception as e:
            logger.error("[UNIFIED ACTIVITY] Failed to query engagement logs: %s", e)
            engagement_total = 0
            raw_logs = []

    # 6. Normalize Events
    normalized_events: list[dict[str, Any]] = []

    for post in raw_posts:
        camp_info = camp_map.get(str(post.get("campaign_id")), {})
        ts = _canonical_publishing_timestamp(post)
        err = (
            sanitize_error_message(post.get("error_message")) if post.get("error_message") else None
        )

        normalized_events.append(
            {
                "id": str(post.get("id")),
                "source_type": "publishing",
                "action_type": "post",
                "status": post.get("status"),
                "timestamp": ts,
                "company_profile_id": (
                    str(camp_info.get("company_profile_id"))
                    if camp_info.get("company_profile_id")
                    else None
                ),
                "linkedin_account_id": (
                    str(post.get("linkedin_account_id"))
                    if post.get("linkedin_account_id")
                    else None
                ),
                "target_context": {
                    "target_id": post.get("unipile_post_id") or str(post.get("id")),
                    "campaign_id": (
                        str(post.get("campaign_id")) if post.get("campaign_id") else None
                    ),
                    "campaign_name": camp_info.get("name"),
                    "hook_preview": (post.get("hook") or post.get("full_content") or "")[:80],
                    "media_url": post.get("media_url"),
                },
                "message": post.get("hook") or post.get("full_content"),
                "error_message": err,
                "metadata": {
                    "slot_id": post.get("slot_id"),
                    "media_type": post.get("media_type"),
                    "unipile_post_id": post.get("unipile_post_id"),
                    "scheduled_at": post.get("scheduled_at"),
                    "published_at": post.get("published_at"),
                    "publishing_started_at": post.get("publishing_started_at"),
                },
            }
        )

    for log in raw_logs:
        ts = _canonical_engagement_timestamp(log)
        err = sanitize_error_message(log.get("error_message")) if log.get("error_message") else None

        normalized_events.append(
            {
                "id": str(log.get("id")),
                "source_type": "engagement",
                "action_type": log.get("action_type"),
                "status": log.get("status"),
                "timestamp": ts,
                "company_profile_id": (
                    str(log.get("company_profile_id")) if log.get("company_profile_id") else None
                ),
                "linkedin_account_id": (
                    str(log.get("linkedin_account_id")) if log.get("linkedin_account_id") else None
                ),
                "target_context": {
                    "target_id": log.get("target_post_id") or log.get("target_profile_id"),
                    "campaign_id": None,
                    "campaign_name": None,
                    "hook_preview": (
                        log.get("comment_text")[:80] if log.get("comment_text") else None
                    ),
                    "media_url": None,
                },
                "message": log.get("comment_text"),
                "error_message": err,
                "metadata": {
                    "target_post_id": log.get("target_post_id"),
                    "target_profile_id": log.get("target_profile_id"),
                    "review_queue_id": (
                        str(log.get("review_queue_id")) if log.get("review_queue_id") else None
                    ),
                    "provider_result_id": log.get("provider_result_id"),
                    "created_at": log.get("created_at"),
                    "completed_at": log.get("completed_at"),
                },
            }
        )

    # 7. Sort newest first by deterministic composite key:
    #    canonical timestamp DESC, source_type DESC, id DESC
    def _parse_ts(ts_str: str) -> float:
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    normalized_events.sort(
        key=lambda ev: (
            _parse_ts(ev["timestamp"]),
            ev.get("source_type", ""),
            str(ev.get("id", "")),
        ),
        reverse=True,
    )

    # 8. Paginate merged results
    total = publishing_total + engagement_total
    paginated_events = normalized_events[offset : offset + limit]
    has_more = (offset + len(paginated_events)) < total

    return {
        "events": paginated_events,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER — Diagnose and reset stuck automation (Brand Scoped)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/circuit-breaker")
async def get_circuit_breaker_status(
    company_profile_id: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get current circuit breaker state for the brand's LinkedIn account."""
    brand = await _resolve_user_brand(str(user.id), company_profile_id)
    account_uuid = brand.get("default_linkedin_account_id")
    if not account_uuid:
        return {"state": "unknown", "reason": "No default LinkedIn account configured for brand"}

    try:
        from src.modules.linkedin.worker.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(str(account_uuid))
        cb_status = cb.get_status()
        cb_status["can_proceed"] = cb.can_proceed()
        cb_status["message"] = (
            "✅ Automation is running normally"
            if cb.can_proceed()
            else f"🔴 Automation HALTED — reason: {cb_status.get('trip_reason', 'unknown')}. Reset to unblock."
        )
        return cb_status
    except Exception as e:
        logger.error("[CIRCUIT BREAKER] Failed to get status for account %s: %s", account_uuid, e)
        return {"state": "unknown", "error": str(e)}


@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker(
    company_profile_id: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Manually reset a tripped circuit breaker for the brand."""
    brand = await _resolve_user_brand(str(user.id), company_profile_id)
    account_uuid = brand.get("default_linkedin_account_id")
    if not account_uuid:
        raise HTTPException(
            status_code=400, detail="No default LinkedIn account configured for brand"
        )

    try:
        from src.modules.linkedin.models import CircuitState

        client = get_supabase_client()
        client.table("linkedin_circuit_breaker").upsert(
            {
                "linkedin_account_id": str(account_uuid),
                "state": CircuitState.CLOSED.value,
                "tripped_at": None,
                "trip_reason": None,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            on_conflict="linkedin_account_id",
        ).execute()
        logger.info("[CIRCUIT BREAKER] Manually reset to CLOSED for account %s", account_uuid)
        return {
            "success": True,
            "new_state": "closed",
            "message": "Circuit breaker reset to CLOSED — automation will resume on next session trigger.",
        }
    except Exception as e:
        logger.error("[CIRCUIT BREAKER] Reset failed for account %s: %s", account_uuid, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
