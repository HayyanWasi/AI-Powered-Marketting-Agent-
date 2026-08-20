"""FastAPI routes for LinkedIn Account Setup and Webhook Registration."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.gateways.unipile_gateway import UnipileGateway

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/linkedin/accounts", tags=["LinkedIn Setup"])


class WebhookRegisterRequest(BaseModel):
    callback_url: str
    events: list[str] = ["new_relation", "new_message"]


@router.get("")
async def list_connected_accounts() -> list[dict[str, Any]]:
    """List all connected LinkedIn accounts from Unipile."""
    gateway = UnipileGateway()
    return await gateway.list_accounts()


@router.get("/{account_id}/status")
async def check_account_status(account_id: str) -> dict[str, Any]:
    """Check health & connection status of a specific LinkedIn account."""
    gateway = UnipileGateway()
    acc = await gateway.get_account(account_id)
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LinkedIn account {account_id} not found in Unipile",
        )
    return acc


@router.post("/webhooks/register")
async def register_webhook(req: WebhookRegisterRequest) -> dict[str, Any]:
    """Register backend webhook URL with Unipile for real-time event notifications."""
    gateway = UnipileGateway()
    success = await gateway.register_webhook(req.callback_url, req.events)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register webhook with Unipile API",
        )
    return {"status": "success", "callback_url": req.callback_url, "events": req.events}
