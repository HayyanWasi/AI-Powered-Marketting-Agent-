"""FastAPI routes for LinkedIn Account Setup and Webhook Registration."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.gateways.unipile_gateway import UnipileGateway
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/linkedin/accounts", tags=["LinkedIn Setup"])


def _configured_gateway() -> UnipileGateway:
    gateway = UnipileGateway()
    if not gateway.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unipile is not configured. Set UNIPILE_DSN and UNIPILE_TOKEN.",
        )
    return gateway


class WebhookRegisterRequest(BaseModel):
    callback_url: str
    events: list[str] = ["new_relation", "new_message"]


@router.get("")
async def list_connected_accounts(
    _user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[dict[str, Any]]:
    """List all connected LinkedIn accounts from Unipile."""
    gateway = _configured_gateway()
    return await gateway.list_accounts()


@router.get("/{account_id}/status")
async def check_account_status(
    account_id: str,
    _user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Check health & connection status of a specific LinkedIn account."""
    gateway = _configured_gateway()
    acc = await gateway.get_account(account_id)
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LinkedIn account {account_id} not found in Unipile",
        )
    return acc


@router.post("/webhooks/register")
async def register_webhook(
    req: WebhookRegisterRequest,
    _user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Register backend webhook URL with Unipile for real-time event notifications."""
    gateway = _configured_gateway()
    success = await gateway.register_webhook(req.callback_url, req.events)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register webhook with Unipile API",
        )
    return {"status": "success", "callback_url": req.callback_url, "events": req.events}


class PublishPostRequest(BaseModel):
    text: str
    account_id: str | None = None


@router.post("/publish")
async def publish_post_now(
    req: PublishPostRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Publish a text post immediately to LinkedIn via Unipile with tenant ownership validation."""
    repo = BaseRepository("linkedin_accounts")
    unipile_account_id: str | None = None

    if req.account_id and req.account_id.strip():
        account_identifier = req.account_id.strip()
        account_row: dict[str, Any] | None = None

        is_uuid = False
        try:
            UUID(account_identifier)
            is_uuid = True
        except (ValueError, TypeError):
            is_uuid = False

        if is_uuid:
            try:
                res = (
                    repo.client.table("linkedin_accounts")
                    .select("*")
                    .eq("id", account_identifier)
                    .limit(1)
                    .execute()
                )
                if res.data:
                    account_row = res.data[0]
            except Exception as e:
                logger.warning("Error querying linkedin_accounts by id: %s", e)

        if not account_row:
            try:
                res = (
                    repo.client.table("linkedin_accounts")
                    .select("*")
                    .eq("unipile_account_id", account_identifier)
                    .limit(1)
                    .execute()
                )
                if res.data:
                    account_row = res.data[0]
            except Exception as e:
                logger.warning("Error querying linkedin_accounts by unipile_account_id: %s", e)

        if not account_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"LinkedIn account {account_identifier} not found",
            )

        if str(account_row.get("user_id")) != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="LinkedIn account does not belong to the authenticated user",
            )

        unipile_account_id = account_row.get("unipile_account_id")
        if not unipile_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LinkedIn account missing unipile_account_id",
            )
    else:
        # Resolve existing connected LinkedIn account owned by authenticated user
        try:
            res = (
                repo.client.table("linkedin_accounts")
                .select("*")
                .eq("user_id", str(user.id))
                .eq("status", "connected")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = res.data or []
        except Exception as e:
            logger.warning("Error querying owned connected linkedin_accounts: %s", e)
            rows = []

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No connected LinkedIn account found for the authenticated user",
            )
        unipile_account_id = rows[0].get("unipile_account_id")
        if not unipile_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connected LinkedIn account is missing unipile_account_id",
            )

    gateway = _configured_gateway()
    post_id = await gateway.create_post(unipile_account_id, req.text)
    if not post_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to publish post to LinkedIn via Unipile. Check account status.",
        )
    return {"status": "success", "post_id": post_id, "message": "Post published to LinkedIn!"}
