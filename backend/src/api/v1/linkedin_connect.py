"""In-app LinkedIn connection via Unipile Hosted Auth.

Flow:
    1. Authenticated user asks for a Hosted Auth link (``POST /link``). The link
       is created entirely server-side; the Unipile API key never reaches the
       frontend — only the hosted URL is returned.
    2. The user completes Hosted Auth on Unipile and is redirected back to the
       app. Unipile also POSTs the result to our ``/notify`` callback.
    3. The callback verifies the account against Unipile (``get_account``),
       confirms it is a LinkedIn account, and upserts a mapping to the user who
       started the flow. Client-supplied account ids are never trusted.
    4. The user reads only their own persisted accounts (``GET ``).

This module creates the verified-account foundation only. It does not change
the existing static ``UNIPILE_ACCOUNT_ID`` behavior, the publisher, or the
engagement workers.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.config.settings import settings
from src.gateways.unipile_gateway import get_unipile_gateway
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/linkedin/connections", tags=["LinkedIn Connections"])

_TABLE = "linkedin_accounts"
_SUCCESS_STATUSES = {"CREATION_SUCCESS", "RECONNECTED"}


def _is_linkedin(account: dict[str, Any]) -> bool:
    """Return True if a Unipile account object represents a LinkedIn account."""
    provider = str(account.get("provider") or account.get("type") or "").upper()
    return "LINKEDIN" in provider


def _public_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


@router.post("/link")
async def create_connection_link(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict[str, str]:
    """Create a LinkedIn-only Hosted Auth link for the authenticated user.

    Returns only the hosted URL. The Unipile API key is used server-side and is
    never exposed to the caller.
    """
    gateway = get_unipile_gateway()
    if not gateway.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unipile is not configured. Set UNIPILE_DSN and UNIPILE_TOKEN.",
        )

    expires_on = (
        datetime.now(UTC) + timedelta(minutes=settings.unipile_hosted_auth_expiry_minutes)
    ).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    hosted_url = await gateway.create_hosted_auth_link(
        name=str(user.id),
        providers=["LINKEDIN"],
        success_redirect_url=_public_url(
            settings.frontend_base_url, "/prospects?linkedin=connected"
        ),
        failure_redirect_url=_public_url(settings.frontend_base_url, "/prospects?linkedin=failed"),
        notify_url=_public_url(settings.app_public_base_url, "/api/v1/linkedin/connections/notify"),
        expires_on=expires_on,
    )

    if not hosted_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create a LinkedIn Hosted Auth link via Unipile.",
        )

    return {"url": hosted_url}


@router.post("/notify")
async def unipile_connect_notify(request: Request) -> dict[str, str]:
    """Receive the Unipile Hosted Auth result and persist a verified mapping.

    Unipile (not the browser) calls this endpoint, echoing back the ``name`` we
    set (the internal user id). We independently verify the account really
    exists and is a LinkedIn account before persisting. Always returns 200 so
    Unipile does not retry-storm; the body reports the outcome.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    status_val = str(payload.get("status") or "").upper()
    account_id = str(payload.get("account_id") or "").strip()
    name = str(payload.get("name") or "").strip()  # our internal user id

    if status_val not in _SUCCESS_STATUSES:
        logger.info("Unipile connect notify: non-success status '%s' — ignored", status_val)
        return {"status": "ignored"}
    if not account_id or not name:
        logger.warning("Unipile connect notify: missing account_id/name — ignored")
        return {"status": "ignored"}

    # ``name`` must be one of our user ids. Never trust an arbitrary value.
    try:
        UUID(name)
    except ValueError:
        logger.warning("Unipile connect notify: 'name' is not a valid user id — rejected")
        return {"status": "rejected"}

    # Verify the account really exists on the provider side.
    gateway = get_unipile_gateway()
    account = await gateway.get_account(account_id)
    if not account:
        logger.warning("Unipile connect notify: account %s failed verification", account_id)
        return {"status": "unverified"}
    if not _is_linkedin(account):
        logger.warning("Unipile connect notify: account %s is not LinkedIn — rejected", account_id)
        return {"status": "rejected"}

    _upsert_account(user_id=name, unipile_account_id=account_id)
    logger.info("LinkedIn account %s connected and verified for user %s", account_id, name)
    return {"status": "ok"}


@router.get("")
async def list_my_connections(
    verify: bool = False,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[dict[str, Any]]:
    """Return only the authenticated user's persisted LinkedIn accounts.

    With ``verify=true`` each account's live Unipile status is refreshed and
    persisted. A user can never see another user's accounts.
    """
    repo = BaseRepository(_TABLE)
    try:
        res = (
            repo.client.table(_TABLE)
            .select("*")
            .eq("user_id", str(user.id))
            .order("created_at", desc=True)
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"linkedin_accounts table not available. Run migration first. ({e})",
        ) from e

    if verify and rows:
        gateway = get_unipile_gateway()
        for row in rows:
            account = await gateway.get_account(row.get("unipile_account_id", ""))
            live_status = "connected" if account and _is_linkedin(account) else "disconnected"
            if live_status != row.get("status"):
                _update_status(repo, row["id"], live_status)
            row["status"] = live_status
            row["last_verified_at"] = datetime.now(UTC).isoformat()

    return rows


def _upsert_account(*, user_id: str, unipile_account_id: str) -> None:
    """Idempotently persist a verified LinkedIn account for a user.

    Keyed on ``unipile_account_id`` (unique), so a duplicate or reconnect
    callback updates the existing row instead of creating a second one.
    """
    repo = BaseRepository(_TABLE)
    now_iso = datetime.now(UTC).isoformat()
    row = {
        "user_id": user_id,
        "unipile_account_id": unipile_account_id,
        "provider": "LINKEDIN",
        "status": "connected",
        "updated_at": now_iso,
        "last_verified_at": now_iso,
    }
    try:
        repo.client.table(_TABLE).upsert(row, on_conflict="unipile_account_id").execute()
    except Exception as e:
        logger.error("Failed to upsert linkedin_account %s: %s", unipile_account_id, e)


def _update_status(repo: BaseRepository, row_id: str, new_status: str) -> None:
    try:
        repo.client.table(_TABLE).update(
            {
                "status": new_status,
                "updated_at": datetime.now(UTC).isoformat(),
                "last_verified_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", row_id).execute()
    except Exception as e:
        logger.error("Failed to update linkedin_account %s status: %s", row_id, e)
