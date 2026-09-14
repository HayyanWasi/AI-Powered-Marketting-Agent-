"""API endpoints for Conversational Campaign Intake."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.models.intake import (
    GuestConfirmRequest,
    IntakeChatRequest,
    IntakeChatResponse,
    IntakeChecklist,
)
from src.repositories.base import BaseRepository
from src.services.intake_chat_service import IntakeChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns/intake", tags=["Campaign Intake"])
intake_service = IntakeChatService()


@router.post("/chat")
async def chat_turn(
    req: IntakeChatRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> IntakeChatResponse:
    """Process a conversational intake chat turn."""
    logger.info(
        "[INTAKE API Step 1] Received chat turn for campaign_id=%s | user_message='%s'",
        req.campaign_id,
        req.user_message,
    )
    from src.repositories.campaign_repository import CampaignRepository

    campaign_repo = CampaignRepository()
    existing_campaign = await campaign_repo.get_by_id(req.campaign_id)
    if existing_campaign and existing_campaign.organization_id != UUID(user.id):
        raise HTTPException(
            status_code=403,
            detail="Access denied: You do not own this campaign intake session.",
        )

    history = await intake_service.get_history(req.campaign_id)
    current_checklist = await intake_service.get_checklist(req.campaign_id)

    res = await intake_service.process_chat_turn(
        campaign_id=req.campaign_id,
        user_message=req.user_message,
        history=history,
        current_checklist=current_checklist,
    )

    logger.info(
        "[INTAKE API Step 2] Chat turn complete for campaign_id=%s | Reply='%s' | Complete=%s",
        req.campaign_id,
        res.get("reply"),
        res.get("is_complete"),
    )
    return IntakeChatResponse.model_validate(res)


@router.get("/{campaign_id}/history")
async def get_intake_history(
    campaign_id: UUID,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Fetch persistent chat history and current checklist for a campaign with ownership check."""
    logger.info("[INTAKE API] Fetching intake history for campaign_id=%s", campaign_id)
    from src.repositories.campaign_repository import CampaignRepository

    campaign_repo = CampaignRepository()
    existing_campaign = await campaign_repo.get_by_id(campaign_id)
    if existing_campaign and existing_campaign.organization_id != UUID(user.id):
        raise HTTPException(
            status_code=403,
            detail="Access denied: You do not own this campaign intake session.",
        )

    history = await intake_service.get_history(campaign_id)
    checklist = await intake_service.get_checklist(campaign_id)

    return {
        "campaign_id": str(campaign_id),
        "history": history,
        "checklist": checklist.model_dump(),
        "is_complete": checklist.is_complete(),
    }


class MigrateIntakeRequest(BaseModel):
    """Migrate intake session from a temporary UUID to the real campaign ID."""

    session_id: UUID  # the temporary UUID used during the intake chat
    campaign_id: UUID  # the real campaign ID returned from POST /campaigns


@router.post("/migrate")
async def migrate_intake_session(
    req: MigrateIntakeRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Re-key the intake checklist from a temporary session UUID to the real campaign ID."""
    logger.info(
        "[INTAKE MIGRATE Step 1] Starting migration from session_id=%s -> campaign_id=%s",
        req.session_id,
        req.campaign_id,
    )
    if req.session_id == req.campaign_id:
        logger.info("[INTAKE MIGRATE] session_id equals campaign_id (no-op).")
        return {"status": "no_op", "message": "session_id and campaign_id are the same"}

    repo = BaseRepository("intake_checklists")
    msg_repo = BaseRepository("intake_messages")

    # 1. Load the checklist saved under the session UUID
    try:
        logger.info("[INTAKE MIGRATE Step 2] Loading checklist for session_id=%s", req.session_id)
        checklist_res = (
            repo.client.table("intake_checklists")
            .select("*")
            .eq("campaign_id", str(req.session_id))
            .execute()
        )
    except Exception as e:
        logger.error(
            "[INTAKE MIGRATE ERROR] Could not load intake checklist for session_id=%s: %s",
            req.session_id,
            e,
        )
        raise HTTPException(status_code=500, detail=f"Could not load intake checklist: {e}")

    if not checklist_res.data:
        logger.warning(
            "[INTAKE MIGRATE WARNING] No intake checklist found for session_id=%s", req.session_id
        )
        return {"status": "not_found", "message": "No intake checklist found for session_id"}

    checklist_row = dict(checklist_res.data[0])
    checklist_row.pop("id", None)  # let DB generate new PK to avoid conflict

    # 2. Upsert under the real campaign_id
    try:
        logger.info(
            "[INTAKE MIGRATE Step 3] Upserting checklist under real campaign_id=%s", req.campaign_id
        )
        checklist_row["campaign_id"] = str(req.campaign_id)
        repo.client.table("intake_checklists").upsert(
            checklist_row, on_conflict="campaign_id"
        ).execute()
        logger.info(
            "[INTAKE MIGRATE Step 3 SUCCESS] Migrated checklist %s -> %s | event='%s' guest='%s'",
            req.session_id,
            req.campaign_id,
            checklist_row.get("event_name"),
            checklist_row.get("guest_name"),
        )
    except Exception as e:
        logger.error(
            "[INTAKE MIGRATE ERROR] Failed to upsert checklist under campaign_id=%s: %s",
            req.campaign_id,
            e,
        )
        raise HTTPException(status_code=500, detail=f"Could not migrate checklist: {e}")

    # 3. Migrate message history (best-effort)
    try:
        logger.info(
            "[INTAKE MIGRATE Step 4] Migrating chat messages for session_id=%s", req.session_id
        )
        msg_res = (
            msg_repo.client.table("intake_messages")
            .select("*")
            .eq("campaign_id", str(req.session_id))
            .execute()
        )
        if msg_res.data:
            migrated = []
            for m in msg_res.data:
                row = dict(m)
                row["campaign_id"] = str(req.campaign_id)
                row.pop("id", None)  # let DB generate new PK
                migrated.append(row)
            msg_repo.client.table("intake_messages").insert(migrated).execute()
        logger.info(
            "[INTAKE MIGRATE Step 4 SUCCESS] Migrated %d messages %s -> %s",
            len(msg_res.data or []),
            req.session_id,
            req.campaign_id,
        )
    except Exception as e:
        logger.warning(
            "[INTAKE MIGRATE WARNING] Could not migrate intake messages (non-fatal): %s", e
        )

    # 4. Delete old session row
    try:
        logger.info(
            "[INTAKE MIGRATE Step 5] Cleaning up old temporary session_id=%s", req.session_id
        )
        repo.client.table("intake_checklists").delete().eq(
            "campaign_id", str(req.session_id)
        ).execute()
        logger.info(
            "[INTAKE MIGRATE Step 5 SUCCESS] Deleted old session row for session_id=%s",
            req.session_id,
        )
    except Exception as e:
        logger.warning("[INTAKE MIGRATE WARNING] Could not delete old session checklist: %s", e)

    return {
        "status": "success",
        "session_id": str(req.session_id),
        "campaign_id": str(req.campaign_id),
        "event_name": checklist_row.get("event_name"),
        "guest_name": checklist_row.get("guest_name"),
    }


@router.post("/confirm-guest")
async def confirm_guest(
    req: GuestConfirmRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Confirm guest details and optionally trigger guest web research."""
    logger.info(
        "[GUEST CONFIRM Step 1] Guest confirmation received for campaign_id=%s | guest_name='%s' | confirmed=%s",
        req.campaign_id,
        req.guest_name,
        req.confirmed,
    )
    checklist = await intake_service.get_checklist(req.campaign_id)

    checklist_dict = checklist.model_dump()
    checklist_dict["has_guest"] = True
    checklist_dict["guest_name"] = req.guest_name
    if req.guest_title:
        checklist_dict["guest_title"] = req.guest_title
    checklist_dict["guest_confirmed"] = req.confirmed

    if req.confirmed:
        logger.info(
            "[GUEST RESEARCH Step 2] Starting DuckDuckGo web search for guest '%s'...",
            req.guest_name,
        )
        try:
            logger.info("[GUEST RESEARCH] Legacy DuckDuckGo autonomous research removed. Skipping.")
            # Future: Call new GuestProfileService here.
            checklist_dict["guest_profile"] = None
        except Exception as e:
            logger.warning("[GUEST RESEARCH ERROR] Error processing guest on confirm: %s", e)

    updated_checklist = IntakeChecklist.model_validate(checklist_dict)
    intake_service._save_checklist(req.campaign_id, updated_checklist)
    logger.info(
        "[GUEST CONFIRM Step 4 SUCCESS] Saved updated checklist with guest research for campaign_id=%s",
        req.campaign_id,
    )

    return {
        "status": "success",
        "campaign_id": str(req.campaign_id),
        "checklist": updated_checklist.model_dump(),
        "is_complete": updated_checklist.is_complete(),
    }


@router.delete("/{campaign_id}")
async def reset_intake_session(
    campaign_id: UUID,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Reset and delete active chat history and checklist for a campaign intake session."""
    intake_service.clear_session(campaign_id)
    return {"status": "success", "message": f"Intake session {campaign_id} reset."}
