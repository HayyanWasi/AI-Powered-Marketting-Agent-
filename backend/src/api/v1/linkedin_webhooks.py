"""FastAPI Webhook Handler for Unipile real-time LinkedIn events."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/linkedin/webhooks", tags=["LinkedIn Webhooks"])


class UnipileEvent(BaseModel):
    """Unipile webhook event payload."""

    event: str
    account_id: str | None = None
    data: dict[str, Any] = {}


@router.post("")
async def receive_unipile_webhook(request: Request) -> Response:
    """Receive and process real-time webhooks from Unipile.

    Handles:
    - new_relation: Prospect accepted connection request -> mark accepted
    - new_message: Prospect replied to message -> stop-on-reply trigger
    """
    try:
        payload = await request.json()
        event_name = payload.get("event") or payload.get("type") or ""
        data = payload.get("data") or payload

        logger.info("Received Unipile webhook event: %s", event_name)

        sequence_repo = BaseRepository("outreach_sequences")

        if event_name in ("new_relation", "relation_accepted"):
            # Connection request accepted!
            provider_id = data.get("provider_id") or data.get("user_id") or ""
            if provider_id:
                (
                    sequence_repo.client.table(sequence_repo.table_name)
                    .update(
                        {
                            "connection_accepted_at": datetime.now(UTC).isoformat(),
                            "current_step": 2,
                            "status": "connected",
                        }
                    )
                    .eq("prospect_linkedin_id", provider_id)
                    .execute()
                )
                logger.info("Updated sequence for prospect %s: Connected", provider_id)

        elif event_name in ("new_message", "message_received"):
            # Prospect replied! Stop-on-reply trigger
            sender_id = data.get("sender_id") or data.get("from_id") or ""
            is_incoming = data.get("is_incoming", True)

            if sender_id and is_incoming:
                (
                    sequence_repo.client.table(sequence_repo.table_name)
                    .update({"status": "replied"})
                    .eq("prospect_linkedin_id", sender_id)
                    .execute()
                )
                logger.info("Prospect %s replied! Outreach sequence paused.", sender_id)

        return Response(status_code=200, content="OK")
    except Exception as e:
        logger.error("Error processing Unipile webhook: %s", e)
        return Response(status_code=200, content="OK")  # Always 200 to prevent retries
