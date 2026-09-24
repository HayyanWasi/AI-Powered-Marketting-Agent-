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
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.config.settings import settings
from src.gateways.unipile_gateway import get_unipile_gateway
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/linkedin/connections", tags=["LinkedIn Connections"])

_TABLE = "linkedin_accounts"
_SUCCESS_STATUSES = {"CREATION_SUCCESS", "RECONNECTED"}
_HOSTED_AUTH_AUDIENCE = "linkedin-hosted-auth-notify"


def _is_linkedin(account: dict[str, Any]) -> bool:
    """Return True if a Unipile account object represents a LinkedIn account."""
    provider = str(account.get("provider") or account.get("type") or "").upper()
    return "LINKEDIN" in provider


def _public_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


def _get_signing_secret() -> str:
    """Retrieve and validate the dedicated Hosted Auth signing secret.

    Fails closed if the secret is unconfigured or shorter than 32 characters.
    Never falls back to a hardcoded secret. Never logs the secret value.
    """
    secret = settings.LINKEDIN_HOSTED_AUTH_SIGNING_SECRET
    if not secret or len(secret.strip()) < 32:
        logger.error("Hosted Auth signing secret is not configured or shorter than 32 characters.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hosted Auth signing secret is not configured or insufficient length",
        )
    return secret.strip()


def _generate_notify_token(user_id: str, expiry_minutes: int) -> str:
    """Generate a signed, expiring URL-safe JWT for Hosted Auth notify callback."""
    secret = _get_signing_secret()
    now = datetime.now(UTC)
    exp = int((now + timedelta(minutes=expiry_minutes)).timestamp())
    claims = {
        "sub": str(user_id),
        "aud": _HOSTED_AUTH_AUDIENCE,
        "exp": exp,
        "iat": int(now.timestamp()),
        "jti": uuid.uuid4().hex,
        "iss": "hipoclipse-backend",
    }
    return jwt.encode(
        claims,
        secret,
        algorithm="HS256",
    )


def _verify_notify_token(token: str | None, expected_user_id: str | None) -> dict[str, Any]:
    """Verify the cryptographically signed notify token.

    Validates:
    - Token presence (raises 400 if missing)
    - Signature validity & non-expiry (raises 403 if invalid or expired)
    - Audience exact match to "linkedin-hosted-auth-notify" (raises 403)
    - Subject is a valid UUID (raises 403)
    - Subject matches the user id carried through the callback (raises 403)
    """
    secret = _get_signing_secret()

    if not token or not str(token).strip():
        logger.warning("Unipile connect notify: missing verification token — rejected")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing notify verification token",
        )

    try:
        payload = jwt.decode(
            token.strip(),
            secret,
            algorithms=["HS256"],
            audience=_HOSTED_AUTH_AUDIENCE,
        )
    except jwt.ExpiredSignatureError as e:
        logger.warning("Unipile connect notify: token expired — rejected")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Notify verification token has expired",
        ) from e
    except jwt.InvalidAudienceError as e:
        logger.warning("Unipile connect notify: invalid token audience — rejected")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid notify verification token audience",
        ) from e
    except jwt.PyJWTError as e:
        logger.warning("Unipile connect notify: invalid token signature/claims — rejected")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid notify verification token",
        ) from e

    token_sub = str(payload.get("sub") or "").strip()
    try:
        UUID(token_sub)
    except ValueError as e:
        logger.warning("Unipile connect notify: token subject is not a valid UUID — rejected")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid notify verification token subject",
        ) from e

    if not expected_user_id or token_sub != expected_user_id.strip():
        logger.warning(
            "Unipile connect notify: token subject does not match payload name — rejected"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token subject does not match callback user identity",
        )

    return payload


def _append_token_to_url(url: str, token: str) -> str:
    """Safely append or update ?token=<token> in a URL, preserving other params."""
    parsed = urlparse(url)
    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query_params["token"] = token
    new_query = urlencode(query_params)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )


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

    token = _generate_notify_token(
        user_id=str(user.id),
        expiry_minutes=settings.unipile_hosted_auth_expiry_minutes,
    )
    raw_notify_url = _public_url(
        settings.app_public_base_url, "/api/v1/linkedin/connections/notify"
    )
    notify_url = _append_token_to_url(raw_notify_url, token)

    hosted_url = await gateway.create_hosted_auth_link(
        name=str(user.id),
        providers=["LINKEDIN"],
        success_redirect_url=_public_url(
            settings.frontend_base_url, "/prospects?linkedin=connected"
        ),
        failure_redirect_url=_public_url(settings.frontend_base_url, "/prospects?linkedin=failed"),
        notify_url=notify_url,
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
    set (the internal user id) and presenting the signed token in query params.
    We verify the token signature, audience, expiry, and user binding before
    processing.
    """
    token = request.query_params.get("token")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    status_val = str(payload.get("status") or "").upper()
    account_id = str(payload.get("account_id") or "").strip()
    name = str(payload.get("name") or "").strip()  # our internal user id

    # Verify cryptographic token and user binding before ANY account processing
    _verify_notify_token(token, name)

    if status_val not in _SUCCESS_STATUSES:
        logger.info("Unipile connect notify: non-success status '%s' — ignored", status_val)
        return {"status": "ignored"}
    if not account_id or not name:
        logger.warning("Unipile connect notify: missing account_id/name — ignored")
        return {"status": "ignored"}

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
