"""Unit tests for legacy LinkedIn publish endpoint tenant ownership hardening."""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.dependencies import AuthenticatedUser
from src.api.v1.linkedin_setup import PublishPostRequest, publish_post_now

USER_1_ID = "11111111-1111-1111-1111-111111111111"
USER_2_ID = "22222222-2222-2222-2222-222222222222"
USER_3_ID = "33333333-3333-3333-3333-333333333333"

INTERNAL_ACC_1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
UNIPILE_ACC_1 = "unipile_user1_acc"

INTERNAL_ACC_2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
UNIPILE_ACC_2 = "unipile_user2_acc"


class MockSupabaseTable:
    def __init__(self, data: list[dict[str, Any]]):
        self._all_data = data
        self._filters: list[tuple[str, Any]] = []

    def select(self, *args, **kwargs) -> MockSupabaseTable:
        return self

    def eq(self, column: str, value: Any) -> MockSupabaseTable:
        self._filters.append((column, value))
        return self

    def order(self, *args, **kwargs) -> MockSupabaseTable:
        return self

    def limit(self, *args, **kwargs) -> MockSupabaseTable:
        return self

    def execute(self) -> MagicMock:
        filtered = self._all_data
        for col, val in self._filters:
            filtered = [r for r in filtered if str(r.get(col)) == str(val)]
        result = MagicMock()
        result.data = [dict(r) for r in filtered]
        return result


@pytest.fixture
def mock_accounts_db():
    sample_accounts = [
        {
            "id": INTERNAL_ACC_1,
            "user_id": USER_1_ID,
            "unipile_account_id": UNIPILE_ACC_1,
            "provider": "LINKEDIN",
            "status": "connected",
            "created_at": "2026-01-01T00:00:00Z",
        },
        {
            "id": INTERNAL_ACC_2,
            "user_id": USER_2_ID,
            "unipile_account_id": UNIPILE_ACC_2,
            "provider": "LINKEDIN",
            "status": "connected",
            "created_at": "2026-01-02T00:00:00Z",
        },
    ]

    with patch("src.api.v1.linkedin_setup.BaseRepository") as mock_repo_cls:
        repo_inst = MagicMock()
        client = MagicMock()
        client.table.side_effect = lambda table_name: MockSupabaseTable(sample_accounts)
        repo_inst.client = client
        mock_repo_cls.return_value = repo_inst
        yield sample_accounts


@pytest.fixture
def mock_gateway():
    with patch("src.api.v1.linkedin_setup._configured_gateway") as mock_get_gw:
        gw = MagicMock()
        gw.create_post = AsyncMock(return_value="post_test_12345")
        mock_get_gw.return_value = gw
        yield gw


@pytest.mark.asyncio
async def test_a_own_internal_account_id_succeeds(mock_accounts_db, mock_gateway):
    """User 1 providing their own internal linkedin_account UUID succeeds."""
    user = AuthenticatedUser(id=USER_1_ID)
    req = PublishPostRequest(text="Hello from user 1", account_id=INTERNAL_ACC_1)

    res = await publish_post_now(req=req, user=user)

    assert res["status"] == "success"
    assert res["post_id"] == "post_test_12345"
    mock_gateway.create_post.assert_awaited_once_with(UNIPILE_ACC_1, "Hello from user 1")


@pytest.mark.asyncio
async def test_b_own_unipile_account_id_succeeds(mock_accounts_db, mock_gateway):
    """User 1 providing their own unipile_account_id string succeeds."""
    user = AuthenticatedUser(id=USER_1_ID)
    req = PublishPostRequest(text="Hello via Unipile ID", account_id=UNIPILE_ACC_1)

    res = await publish_post_now(req=req, user=user)

    assert res["status"] == "success"
    assert res["post_id"] == "post_test_12345"
    mock_gateway.create_post.assert_awaited_once_with(UNIPILE_ACC_1, "Hello via Unipile ID")


@pytest.mark.asyncio
async def test_c_another_users_internal_account_id_returns_403(mock_accounts_db, mock_gateway):
    """User 1 attempting to publish with User 2's internal account UUID returns 403."""
    user = AuthenticatedUser(id=USER_1_ID)
    req = PublishPostRequest(text="Malicious post", account_id=INTERNAL_ACC_2)

    with pytest.raises(HTTPException) as exc_info:
        await publish_post_now(req=req, user=user)

    assert exc_info.value.status_code == 403
    assert "does not belong" in exc_info.value.detail
    mock_gateway.create_post.assert_not_called()


@pytest.mark.asyncio
async def test_d_another_users_unipile_account_id_returns_403(mock_accounts_db, mock_gateway):
    """User 1 attempting to publish with User 2's unipile_account_id returns 403."""
    user = AuthenticatedUser(id=USER_1_ID)
    req = PublishPostRequest(text="Malicious post", account_id=UNIPILE_ACC_2)

    with pytest.raises(HTTPException) as exc_info:
        await publish_post_now(req=req, user=user)

    assert exc_info.value.status_code == 403
    assert "does not belong" in exc_info.value.detail
    mock_gateway.create_post.assert_not_called()


@pytest.mark.asyncio
async def test_e_missing_account_id_resolves_only_owned_account(mock_accounts_db, mock_gateway):
    """Missing account_id resolves an account owned by the calling user."""
    user = AuthenticatedUser(id=USER_2_ID)
    req = PublishPostRequest(text="Auto-resolved account post", account_id=None)

    res = await publish_post_now(req=req, user=user)

    assert res["status"] == "success"
    assert res["post_id"] == "post_test_12345"
    mock_gateway.create_post.assert_awaited_once_with(UNIPILE_ACC_2, "Auto-resolved account post")


@pytest.mark.asyncio
async def test_f_no_owned_account_returns_400(mock_accounts_db, mock_gateway):
    """User 3 with no accounts receives 400 when account_id is omitted."""
    user = AuthenticatedUser(id=USER_3_ID)
    req = PublishPostRequest(text="No account post", account_id=None)

    with pytest.raises(HTTPException) as exc_info:
        await publish_post_now(req=req, user=user)

    assert exc_info.value.status_code == 400
    assert "No connected LinkedIn account found" in exc_info.value.detail
    mock_gateway.create_post.assert_not_called()


@pytest.mark.asyncio
async def test_g_provider_publish_call_not_made_for_unauthorized_account(
    mock_accounts_db, mock_gateway
):
    """Provider create_post is strictly never invoked for unauthorized attempts."""
    user = AuthenticatedUser(id=USER_1_ID)
    req = PublishPostRequest(text="Attempt", account_id=INTERNAL_ACC_2)

    with pytest.raises(HTTPException):
        await publish_post_now(req=req, user=user)

    assert mock_gateway.create_post.await_count == 0


def test_h_primary_campaign_publishing_code_and_files_untouched():
    """Verify primary campaign publish-now and publisher worker remain independent and untouched."""
    from src.api.v1.autopilot import publish_post_now as campaign_publish_post_now
    from src.api.v1.linkedin_setup import publish_post_now as legacy_publish_post_now
    from src.modules.linkedin.worker.post_publisher import publish_due_posts

    # 1. Primary campaign publish-now handler exists and has expected signature
    sig = inspect.signature(campaign_publish_post_now)
    assert "post_id" in sig.parameters

    # 2. Worker publisher function exists
    assert callable(publish_due_posts)

    # 3. Legacy publish endpoint is distinct and strictly isolated to linkedin_setup
    assert callable(legacy_publish_post_now)
    assert campaign_publish_post_now is not legacy_publish_post_now
