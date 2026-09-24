"""Unit tests for Hosted Auth notify callback token verification & replay hardening."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.api.v1.linkedin_connect import (
    _HOSTED_AUTH_AUDIENCE,
    _generate_notify_token,
    unipile_connect_notify,
)
from src.config.settings import Settings, settings


def _make_request(
    query_params: dict[str, str] | None = None, json_body: dict[str, Any] | None = None
) -> Request:
    """Helper to build a Starlette Request with query string and async JSON body."""
    from urllib.parse import urlencode

    query_bytes = urlencode(query_params or {}).encode("utf-8")
    body_bytes = json.dumps(json_body or {}).encode("utf-8")

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body_bytes}

    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/linkedin/connections/notify",
        "query_string": query_bytes,
        "headers": [(b"content-type", b"application/json")],
    }
    return Request(scope, receive)


@pytest.fixture
def mock_gateway():
    with patch("src.api.v1.linkedin_connect.get_unipile_gateway") as mock_get_gw:
        gw = MagicMock()
        gw.get_account = AsyncMock(return_value={"id": "acc-123", "provider": "LINKEDIN"})
        mock_get_gw.return_value = gw
        yield gw


@pytest.fixture
def mock_upsert():
    with patch("src.api.v1.linkedin_connect._upsert_account") as mock_ups:
        yield mock_ups


@pytest.mark.asyncio
async def test_valid_signed_callback_succeeds(mock_gateway, mock_upsert):
    """A. Valid signed callback with matching claims succeeds."""
    user_id = str(uuid.uuid4())
    account_id = "unipile-acc-999"

    token = _generate_notify_token(user_id=user_id, expiry_minutes=15)
    req = _make_request(
        query_params={"token": token},
        json_body={"status": "CREATION_SUCCESS", "account_id": account_id, "name": user_id},
    )

    res = await unipile_connect_notify(req)
    assert res == {"status": "ok"}
    mock_upsert.assert_called_once_with(user_id=user_id, unipile_account_id=account_id)


@pytest.mark.asyncio
async def test_missing_token_rejected(mock_gateway, mock_upsert):
    """B. Missing token is rejected with 400 and performs no account upsert."""
    user_id = str(uuid.uuid4())
    req = _make_request(
        query_params={},
        json_body={"status": "CREATION_SUCCESS", "account_id": "acc-123", "name": user_id},
    )

    with pytest.raises(HTTPException) as exc_info:
        await unipile_connect_notify(req)

    assert exc_info.value.status_code == 400
    assert "Missing notify verification token" in exc_info.value.detail
    mock_upsert.assert_not_called()


@pytest.mark.asyncio
async def test_tampered_token_rejected(mock_gateway, mock_upsert):
    """C. Tampered token signature is rejected with 403 and performs no account upsert."""
    user_id = str(uuid.uuid4())
    tampered_token = jwt.encode(
        {
            "sub": user_id,
            "aud": _HOSTED_AUTH_AUDIENCE,
            "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
        },
        "wrong-secret-key-that-does-not-match-settings-32chars",
        algorithm="HS256",
    )
    req = _make_request(
        query_params={"token": tampered_token},
        json_body={"status": "CREATION_SUCCESS", "account_id": "acc-123", "name": user_id},
    )

    with pytest.raises(HTTPException) as exc_info:
        await unipile_connect_notify(req)

    assert exc_info.value.status_code == 403
    assert "Invalid notify verification token" in exc_info.value.detail
    mock_upsert.assert_not_called()


@pytest.mark.asyncio
async def test_expired_token_rejected(mock_gateway, mock_upsert):
    """D. Expired token is rejected with 403 and performs no account upsert."""
    user_id = str(uuid.uuid4())
    past = int((datetime.now(UTC) - timedelta(minutes=5)).timestamp())
    expired_token = jwt.encode(
        {"sub": user_id, "aud": _HOSTED_AUTH_AUDIENCE, "exp": past},
        settings.LINKEDIN_HOSTED_AUTH_SIGNING_SECRET,
        algorithm="HS256",
    )
    req = _make_request(
        query_params={"token": expired_token},
        json_body={"status": "CREATION_SUCCESS", "account_id": "acc-123", "name": user_id},
    )

    with pytest.raises(HTTPException) as exc_info:
        await unipile_connect_notify(req)

    assert exc_info.value.status_code == 403
    assert "expired" in exc_info.value.detail.lower()
    mock_upsert.assert_not_called()


@pytest.mark.asyncio
async def test_wrong_audience_rejected(mock_gateway, mock_upsert):
    """E. Token with wrong audience is rejected with 403 and performs no account upsert."""
    user_id = str(uuid.uuid4())
    wrong_aud_token = jwt.encode(
        {
            "sub": user_id,
            "aud": "wrong-audience-not-hosted-auth",
            "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
        },
        settings.LINKEDIN_HOSTED_AUTH_SIGNING_SECRET,
        algorithm="HS256",
    )
    req = _make_request(
        query_params={"token": wrong_aud_token},
        json_body={"status": "CREATION_SUCCESS", "account_id": "acc-123", "name": user_id},
    )

    with pytest.raises(HTTPException) as exc_info:
        await unipile_connect_notify(req)

    assert exc_info.value.status_code == 403
    assert "audience" in exc_info.value.detail.lower()
    mock_upsert.assert_not_called()


@pytest.mark.asyncio
async def test_subject_user_mismatch_rejected(mock_gateway, mock_upsert):
    """F. Token subject mismatching the payload user id is rejected with 403."""
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())

    token = _generate_notify_token(user_id=user_a, expiry_minutes=15)
    req = _make_request(
        query_params={"token": token},
        json_body={"status": "CREATION_SUCCESS", "account_id": "acc-123", "name": user_b},
    )

    with pytest.raises(HTTPException) as exc_info:
        await unipile_connect_notify(req)

    assert exc_info.value.status_code == 403
    assert "does not match" in exc_info.value.detail
    mock_upsert.assert_not_called()


@pytest.mark.asyncio
async def test_repeated_identical_callback_is_idempotent(mock_gateway, mock_upsert):
    """G. Repeated identical valid callback succeeds and invokes idempotent upsert."""
    user_id = str(uuid.uuid4())
    account_id = "unipile-acc-idempotent"

    token = _generate_notify_token(user_id=user_id, expiry_minutes=15)
    body = {"status": "CREATION_SUCCESS", "account_id": account_id, "name": user_id}

    req1 = _make_request(query_params={"token": token}, json_body=body)
    res1 = await unipile_connect_notify(req1)
    assert res1 == {"status": "ok"}

    req2 = _make_request(query_params={"token": token}, json_body=body)
    res2 = await unipile_connect_notify(req2)
    assert res2 == {"status": "ok"}

    assert mock_upsert.call_count == 2
    mock_upsert.assert_called_with(user_id=user_id, unipile_account_id=account_id)


@pytest.mark.asyncio
async def test_failed_verification_performs_no_account_upsert(mock_gateway, mock_upsert):
    """H. Verification failure on malformed token performs no account upsert."""
    req = _make_request(
        query_params={"token": "not-even-a-jwt"},
        json_body={
            "status": "CREATION_SUCCESS",
            "account_id": "acc-123",
            "name": str(uuid.uuid4()),
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        await unipile_connect_notify(req)

    assert exc_info.value.status_code == 403
    mock_upsert.assert_not_called()


def test_missing_signing_secret_fails_closed_in_generation():
    """Fail-closed: token generation raises HTTP 500 when secret is None or empty."""
    with patch.object(settings, "LINKEDIN_HOSTED_AUTH_SIGNING_SECRET", None):
        with pytest.raises(HTTPException) as exc_info:
            _generate_notify_token(user_id=str(uuid.uuid4()), expiry_minutes=15)
        assert exc_info.value.status_code == 500
        assert "not configured" in exc_info.value.detail


@pytest.mark.asyncio
async def test_missing_signing_secret_fails_closed_in_notify(mock_gateway, mock_upsert):
    """Fail-closed: callback verification raises HTTP 500 when secret is None."""
    req = _make_request(
        query_params={"token": "some-token"},
        json_body={
            "status": "CREATION_SUCCESS",
            "account_id": "acc-123",
            "name": str(uuid.uuid4()),
        },
    )
    with patch.object(settings, "LINKEDIN_HOSTED_AUTH_SIGNING_SECRET", None):
        with pytest.raises(HTTPException) as exc_info:
            await unipile_connect_notify(req)
        assert exc_info.value.status_code == 500
        mock_upsert.assert_not_called()


def test_short_signing_secret_fails_closed():
    """Fail-closed: secret shorter than 32 characters raises HTTP 500."""
    with patch.object(settings, "LINKEDIN_HOSTED_AUTH_SIGNING_SECRET", "too-short-key"):
        with pytest.raises(HTTPException) as exc_info:
            _generate_notify_token(user_id=str(uuid.uuid4()), expiry_minutes=15)
        assert exc_info.value.status_code == 500
        assert "insufficient length" in exc_info.value.detail


def test_no_hardcoded_fallback_in_settings_definition():
    """Settings class default must be None (no hardcoded fallback secret in source)."""
    fresh_settings = Settings(_env_file=None, LINKEDIN_HOSTED_AUTH_SIGNING_SECRET=None)
    assert fresh_settings.LINKEDIN_HOSTED_AUTH_SIGNING_SECRET is None


def test_production_validation_rejects_missing_signing_secret():
    """Production mode requires configured LINKEDIN_HOSTED_AUTH_SIGNING_SECRET with len >= 32."""
    with pytest.raises(ValueError, match="LINKEDIN_HOSTED_AUTH_SIGNING_SECRET must be configured"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            LINKEDIN_HOSTED_AUTH_SIGNING_SECRET=None,
        )

    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            LINKEDIN_HOSTED_AUTH_SIGNING_SECRET="short-key",
        )
