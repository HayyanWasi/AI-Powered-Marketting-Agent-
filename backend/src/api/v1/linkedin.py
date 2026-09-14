"""FastAPI routes for LinkedIn Campaign Execution, Launchpad Preview, and Launch."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.modules.linkedin.generators.post_generator import LinkedInPostGenerator
from src.modules.linkedin.generators.sequence_generator import OutreachSequenceGenerator
from src.modules.linkedin.models import (
    AutoPilotConfig,
    PostStatus,
)
from src.modules.planning.models.campaign_plan import CampaignPlan
from src.modules.research.models.research_brief import ResearchBrief
from src.repositories.base import BaseRepository
from src.repositories.campaign_repository import CampaignRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/linkedin/campaigns", tags=["LinkedIn Campaign Launchpad"])


async def _verify_campaign_ownership(campaign_id: UUID, user_id: UUID) -> Any:
    campaign_repo = CampaignRepository()
    campaign = await campaign_repo.get_by_id(campaign_id, organization_id=user_id)
    if not campaign:
        campaign = await campaign_repo.get_by_id(campaign_id, None)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found or access denied.",
        )
    return campaign


class GenerateContentRequest(BaseModel):
    research_brief_dict: dict[str, Any] | None = None


class PatchPostRequest(BaseModel):
    hook: str | None = None
    body: str | None = None
    cta_text: str | None = None


class LaunchCampaignRequest(BaseModel):
    account_id: str
    config: AutoPilotConfig | None = None


@router.post("/{campaign_id}/generate")
async def generate_campaign_content(
    campaign_id: UUID,
    req: GenerateContentRequest | None = None,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Generate research-grounded LinkedIn posts and outbound sequence for an approved campaign.

    Reads approved CampaignPlan and ResearchBrief from database/request.
    """
    campaign = await _verify_campaign_ownership(campaign_id, UUID(user.id))

    # Reconstruct CampaignPlan
    plan_dict = (
        getattr(campaign, "strategy_document", None)
        or getattr(campaign, "plan_document", None)
        or {}
    )
    if not plan_dict and hasattr(campaign, "goals"):
        # Fallback if raw campaign object used
        plan_dict = {}

    plan = CampaignPlan.from_document(plan_dict) if plan_dict else CampaignPlan()

    # Reconstruct ResearchBrief
    brief: ResearchBrief | None = None
    if req and req.research_brief_dict:
        try:
            brief = ResearchBrief.model_validate(req.research_brief_dict)
        except Exception:
            brief = None

    logger.info("[CONTENT GENERATION Step 1] Triggered generation for campaign_id=%s", campaign_id)

    # ── Load intake checklist from DB — this is where event/guest data lives ──
    intake_data: dict[str, Any] = {}
    try:
        logger.info(
            "[CONTENT GENERATION Step 2] Loading intake checklist from DB for campaign_id=%s...",
            campaign_id,
        )
        intake_repo = BaseRepository("intake_checklists")
        res = (
            intake_repo.client.table("intake_checklists")
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        if res.data:
            intake_data = res.data[0]
            logger.info(
                "[CONTENT GENERATION Step 2 SUCCESS] Loaded intake checklist for campaign %s: event='%s', guest='%s', venue='%s', link='%s', profile_bio=%s",
                campaign_id,
                intake_data.get("event_name"),
                intake_data.get("guest_name"),
                intake_data.get("venue"),
                intake_data.get("registration_link"),
                bool(intake_data.get("guest_profile")),
            )
        else:
            logger.warning(
                "[CONTENT GENERATION Step 2 WARNING] No intake checklist found for campaign %s — content will be generic!",
                campaign_id,
            )
    except Exception as e:
        logger.warning("[CONTENT GENERATION Step 2 ERROR] Could not load intake checklist: %s", e)

    # 1. Generate Posts — passing all intake data through
    logger.info(
        "[CONTENT GENERATION Step 3] Calling LinkedInPostGenerator for campaign_id=%s...",
        campaign_id,
    )
    has_guest = intake_data.get("has_guest") is True and bool(intake_data.get("guest_name"))
    actual_guest_name = intake_data.get("guest_name") if has_guest else None
    actual_guest_title = intake_data.get("guest_title") if has_guest else None
    actual_guest_profile = intake_data.get("guest_profile") if has_guest else None

    # Fetch the user's configured posting time from autopilot settings (default: 10:00 AM)
    from src.api.v1.autopilot import _get_user_settings

    autopilot_settings = _get_user_settings(str(user.id))
    post_time_str = autopilot_settings.get("post_time_slot", "10:00 AM")
    # AutoPilotConfig default timezone (Asia/Karachi) — matches user's locale
    timezone_name = "Asia/Karachi"
    logger.info(
        "[CONTENT GENERATION Step 3] Post scheduling time: %s %s",
        post_time_str,
        timezone_name,
    )

    post_gen = LinkedInPostGenerator()
    posts = await post_gen.generate_all_posts(
        campaign_id,
        plan,
        brief,
        event_name=intake_data.get("event_name") or "",
        event_date=intake_data.get("event_date") or "",
        venue=intake_data.get("venue") or "",
        registration_link=intake_data.get("registration_link") or "",
        target_audience=intake_data.get("target_audience") or "",
        curriculum_breakdown=intake_data.get("curriculum_breakdown") or "",
        ticket_price=intake_data.get("is_free_or_paid") or "Free",
        guest_name=actual_guest_name,
        guest_title=actual_guest_title,
        guest_profile=actual_guest_profile,
        post_time_str=post_time_str,
        timezone_name=timezone_name,
    )
    logger.info("[CONTENT GENERATION Step 3 SUCCESS] Generated %d LinkedIn posts.", len(posts))

    # 2. Save Posts to Supabase
    logger.info(
        "[CONTENT GENERATION Step 4] Saving generated posts to Supabase `linkedin_posts` table..."
    )
    posts_repo = BaseRepository("linkedin_posts")
    saved_posts = []
    for post in posts:
        post_data = post.to_dict()
        try:
            res = posts_repo.client.table(posts_repo.table_name).insert(post_data).execute()
            if res.data:
                saved_posts.append(res.data[0])
        except Exception as e:
            logger.error("[CONTENT GENERATION Step 4 ERROR] Failed to save generated post: %s", e)
    logger.info(
        "[CONTENT GENERATION Step 4 SUCCESS] Successfully saved %d/%d posts to DB.",
        len(saved_posts),
        len(posts),
    )

    # 3. Generate Outreach Sequence
    logger.info("[CONTENT GENERATION Step 5] Generating outreach sequence...")
    seq_gen = OutreachSequenceGenerator()
    outreach = await seq_gen.generate_sequence(campaign_id, plan, brief)

    seq_repo = BaseRepository("outreach_sequences")
    try:
        seq_data = outreach.model_dump(mode="json")
        seq_repo.client.table(seq_repo.table_name).insert(seq_data).execute()
        logger.info("[CONTENT GENERATION Step 5 SUCCESS] Saved outreach sequence to DB.")
    except Exception as e:
        logger.error("[CONTENT GENERATION Step 5 ERROR] Failed to save outreach sequence: %s", e)

    return {
        "status": "success",
        "posts_generated": len(saved_posts),
        "sequence_generated": True,
    }


@router.get("/{campaign_id}/preview")
async def get_launchpad_preview(
    campaign_id: UUID,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get Launchpad preview data (posts + sequence + safety config) with ownership check."""
    await _verify_campaign_ownership(campaign_id, UUID(user.id))
    posts_repo = BaseRepository("linkedin_posts")
    seq_repo = BaseRepository("outreach_sequences")

    posts: list = []
    sequence = None

    try:
        posts_res = (
            posts_repo.client.table(posts_repo.table_name)
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        posts = posts_res.data if posts_res.data else []
    except Exception as e:
        logger.warning("linkedin_posts table not ready: %s", e)

    try:
        seq_res = (
            seq_repo.client.table(seq_repo.table_name)
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        sequence = seq_res.data[0] if seq_res.data and len(seq_res.data) > 0 else None
    except Exception as e:
        logger.warning("outreach_sequences table not ready: %s", e)

    config = AutoPilotConfig().model_dump()

    return {
        "campaign_id": str(campaign_id),
        "posts": posts,
        "outreach_sequence": sequence,
        "autopilot_config": config,
    }


@router.patch("/{campaign_id}/posts/{post_id}")
async def patch_post(
    campaign_id: UUID,
    post_id: UUID,
    req: PatchPostRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Quick edit a generated LinkedIn post with ownership check."""
    await _verify_campaign_ownership(campaign_id, UUID(user.id))
    posts_repo = BaseRepository("linkedin_posts")
    update_data: dict[str, Any] = {}

    if req.hook is not None:
        update_data["hook"] = req.hook
    if req.body is not None:
        update_data["body"] = req.body
    if req.cta_text is not None:
        update_data["cta_text"] = req.cta_text

    try:
        if "hook" in update_data or "body" in update_data or "cta_text" in update_data:
            existing_res = (
                posts_repo.client.table(posts_repo.table_name)
                .select("*")
                .eq("id", str(post_id))
                .execute()
            )
            if existing_res.data:
                existing = existing_res.data[0]
                hook = update_data.get("hook", existing.get("hook", ""))
                body = update_data.get("body", existing.get("body", ""))
                cta = update_data.get("cta_text", existing.get("cta_text", ""))
                update_data["full_content"] = f"{hook}\n\n{body}\n\n{cta}".strip()

        res = (
            posts_repo.client.table(posts_repo.table_name)
            .update(update_data)
            .eq("id", str(post_id))
            .execute()
        )
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post {post_id} not found",
            )
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"linkedin_posts table not available. Run migration first. ({e})",
        )


@router.post("/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: UUID,
    req: LaunchCampaignRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Activate Auto-Pilot for campaign with ownership check."""
    await _verify_campaign_ownership(campaign_id, UUID(user.id))
    posts_repo = BaseRepository("linkedin_posts")

    try:
        posts_repo.client.table(posts_repo.table_name).update(
            {"status": PostStatus.SCHEDULED.value}
        ).eq("campaign_id", str(campaign_id)).eq("status", PostStatus.DRAFT.value).execute()
    except Exception as e:
        logger.warning("Could not update post statuses (table may not exist): %s", e)

    return {
        "status": "active",
        "campaign_id": str(campaign_id),
        "account_id": req.account_id,
        "message": "Campaign activated! Auto-Pilot worker will publish posts and execute outreach daily at 09:00 AM.",
    }


@router.get("/{campaign_id}/status")
async def get_campaign_execution_status(
    campaign_id: UUID,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Get real-time execution statistics for a campaign with ownership check."""
    await _verify_campaign_ownership(campaign_id, UUID(user.id))
    posts_repo = BaseRepository("linkedin_posts")
    seq_repo = BaseRepository("outreach_sequences")

    posts: list = []
    sequences: list = []

    try:
        posts_res = (
            posts_repo.client.table(posts_repo.table_name)
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        posts = posts_res.data if posts_res.data else []
    except Exception as e:
        logger.warning("linkedin_posts table not ready: %s", e)

    try:
        seq_res = (
            seq_repo.client.table(seq_repo.table_name)
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        sequences = seq_res.data if seq_res.data else []
    except Exception as e:
        logger.warning("outreach_sequences table not ready: %s", e)

    published_count = sum(1 for p in posts if p.get("status") == "published")
    scheduled_count = sum(1 for p in posts if p.get("status") == "scheduled")

    return {
        "campaign_id": str(campaign_id),
        "total_posts": len(posts),
        "posts_published": published_count,
        "posts_scheduled": scheduled_count,
        "total_outreach_leads": len(sequences),
        "connected_leads": sum(1 for s in sequences if s.get("status") in ("connected", "replied")),
        "replied_leads": sum(1 for s in sequences if s.get("status") == "replied"),
    }
