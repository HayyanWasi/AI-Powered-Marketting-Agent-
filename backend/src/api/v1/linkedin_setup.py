"""FastAPI routes for LinkedIn Account Setup and Webhook Registration."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.gateways.unipile_gateway import UnipileGateway

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
    _user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, Any]:
    """Publish a text post immediately to LinkedIn via Unipile."""
    from src.config.settings import settings

    gateway = _configured_gateway()
    account_id = req.account_id or settings.unipile_account_id
    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No UNIPILE_ACCOUNT_ID configured in settings",
        )
    post_id = await gateway.create_post(account_id, req.text)
    if not post_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to publish post to LinkedIn via Unipile. Check account status.",
        )
    return {"status": "success", "post_id": post_id, "message": "Post published to LinkedIn!"}
