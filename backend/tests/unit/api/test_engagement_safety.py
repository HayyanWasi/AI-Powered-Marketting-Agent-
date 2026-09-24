"""Comprehensive Engagement Safety Architecture Unit & Tenancy Tests.

All tests use strictly mocked Unipile gateway and in-memory mock repositories;
ZERO real LinkedIn API calls, likes, comments, or connection requests are made.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.config.settings import settings
from src.main import app
from src.modules.linkedin.account_resolver import (
    BrandAccountResolutionError,
    resolve_brand_linkedin_account,
)
from src.modules.linkedin.distributed_lock import BrandAdvisoryLock
from src.modules.linkedin.models import (
    TargetPost,
)
from src.modules.linkedin.worker.session_executor import EngagementSessionExecutor

# ═══════════════════════════════════════════════════════════════════════════════
# Mock Database Infrastructure for In-Memory Unit Isolation
# ═══════════════════════════════════════════════════════════════════════════════


class MockTable:
    def __init__(self, data_list: list[dict[str, Any]]):
        self.data_list = data_list
        self._filters: dict[str, Any] = {}
        self._order_by: str | None = None
        self._desc = False
        self._limit: int | None = None
        self._updates: dict[str, Any] | None = None
        self._insert_data: Any = None
        self._upsert_data: Any = None
        self._is_delete: bool = False
        self._last_result: list[dict[str, Any]] = []

    @property
    def data(self) -> list[dict[str, Any]]:
        return self._last_result

    def select(self, *args: Any, **kwargs: Any) -> MockTable:
        return self

    def insert(self, record: dict[str, Any] | list[dict[str, Any]]) -> MockTable:
        self._insert_data = record
        return self

    def upsert(self, record: dict[str, Any], on_conflict: str = "") -> MockTable:
        self._upsert_data = record
        return self

    def update(self, updates: dict[str, Any]) -> MockTable:
        self._updates = updates
        return self

    def delete(self) -> MockTable:
        self._is_delete = True
        return self

    def eq(self, field: str, value: Any) -> MockTable:
        self._filters[field] = str(value) if isinstance(value, UUID) else value
        return self

    def order(self, field: str, desc: bool = False) -> MockTable:
        self._order_by = field
        self._desc = desc
        return self

    def limit(self, count: int) -> MockTable:
        self._limit = count
        return self

    def _matching_rows(self) -> list[dict[str, Any]]:
        matches = []
        for row in self.data_list:
            match = True
            for k, v in self._filters.items():
                row_val = row.get(k)
                if isinstance(row_val, UUID):
                    row_val = str(row_val)
                if str(row_val) != str(v):
                    match = False
                    break
            if match:
                matches.append(row)
        return matches

    def execute(self) -> SimpleNamespace:
        if self._insert_data is not None:
            records = (
                [self._insert_data] if isinstance(self._insert_data, dict) else self._insert_data
            )
            inserted = []
            for r in records:
                copied = dict(r)
                if "id" not in copied:
                    copied["id"] = str(uuid4())
                self.data_list.append(copied)
                inserted.append(copied)
            self._insert_data = None
            self._last_result = inserted
            return SimpleNamespace(data=inserted)

        if self._upsert_data is not None:
            copied = dict(self._upsert_data)
            if "id" not in copied:
                copied["id"] = str(uuid4())
            self.data_list.append(copied)
            self._upsert_data = None
            self._last_result = [copied]
            return SimpleNamespace(data=[copied])

        matching = self._matching_rows()

        if self._updates is not None:
            updated = []
            for row in matching:
                row.update(self._updates)
                updated.append(dict(row))
            self._updates = None
            self._last_result = updated
            return SimpleNamespace(data=updated)

        if self._is_delete:
            deleted = []
            for r in list(matching):
                if r in self.data_list:
                    self.data_list.remove(r)
                    deleted.append(dict(r))
            self._is_delete = False
            self._last_result = deleted
            return SimpleNamespace(data=deleted)

        rows = [dict(r) for r in matching]
        if self._limit is not None:
            rows = rows[: self._limit]
        self._last_result = rows
        return SimpleNamespace(data=rows)


class MockSupabaseClient:
    def __init__(self, stores: dict[str, list[dict[str, Any]]]):
        self.stores = stores

    def table(self, table_name: str) -> MockTable:
        if table_name not in self.stores:
            self.stores[table_name] = []
        return MockTable(self.stores[table_name])

    def rpc(self, fn_name: str, params: dict[str, Any]):
        return SimpleNamespace(data=[])


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DATABASE MIGRATIONS VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════


def test_migration_025_defines_constraints_and_permanent_indexes():
    mig_025 = (
        (
            Path(__file__).resolve().parents[3]
            / "migrations"
            / "025_create_engagement_settings_and_logs.up.sql"
        )
        .read_text(encoding="utf-8")
        .lower()
    )

    assert "create table if not exists public.linkedin_engagement_settings" in mig_025
    assert "company_profile_id" in mig_025
    assert "uq_engagement_settings_brand" in mig_025
    assert "enable row level security" in mig_025

    assert "create table if not exists public.linkedin_engagement_log" in mig_025
    # Check unconditional permanent unique indexes (NO WHERE status = ...)
    assert "uq_engagement_log_account_post_like" in mig_025
    assert "uq_engagement_log_account_post_comment" in mig_025
    assert "uq_engagement_log_account_profile_invite" in mig_025
    assert "where status" not in mig_025  # Permanent across all statuses


def test_migration_026_defines_brand_scoping_and_dedupe():
    mig_026 = (
        (
            Path(__file__).resolve().parents[3]
            / "migrations"
            / "026_scope_personas_and_review_queue.up.sql"
        )
        .read_text(encoding="utf-8")
        .lower()
    )

    assert "uq_target_personas_brand_label" in mig_026
    assert "uq_review_queue_account_post" in mig_026
    assert "linkedin_accounts.id" in mig_026 or "references public.linkedin_accounts(id)" in mig_026


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TENANCY & BRAND SCOPING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


def test_user_a_cannot_read_or_write_user_b_settings():
    user_a = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    user_b = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])

    brand_b_id = str(uuid4())
    stores = {
        "company_profiles": [{"id": brand_b_id, "user_id": user_b.id, "company_name": "Brand B"}],
        "linkedin_engagement_settings": [
            {
                "id": str(uuid4()),
                "user_id": user_b.id,
                "company_profile_id": brand_b_id,
                "engagement_enabled": True,
                "likes_per_day": 30,
            }
        ],
    }

    mock_client = MockSupabaseClient(stores)

    app.dependency_overrides[get_authenticated_user] = lambda: user_a
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        # User A attempts to read User B's brand settings -> 404/403
        resp = client.get(f"/api/v1/autopilot/settings?company_profile_id={brand_b_id}")
        assert resp.status_code in (403, 404)

        # User A attempts to update User B's brand settings -> 404/403
        update_resp = client.put(
            "/api/v1/autopilot/settings",
            json={"company_profile_id": brand_b_id, "likes_per_day": 5},
        )
        assert update_resp.status_code in (403, 404)

    app.dependency_overrides.clear()


def test_user_a_cannot_access_user_b_personas():
    user_a = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    user_b = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    brand_a_id = str(uuid4())
    brand_b_id = str(uuid4())
    persona_b_id = str(uuid4())

    stores = {
        "company_profiles": [
            {"id": brand_a_id, "user_id": user_a.id},
            {"id": brand_b_id, "user_id": user_b.id},
        ],
        "linkedin_target_personas": [
            {
                "id": persona_b_id,
                "user_id": user_b.id,
                "company_profile_id": brand_b_id,
                "label": "CEOs",
                "search_keywords": "CEO",
                "max_profiles": 50,
            }
        ],
    }
    mock_client = MockSupabaseClient(stores)

    app.dependency_overrides[get_authenticated_user] = lambda: user_a
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        # User A attempts to delete persona owned by User B -> 404 (does not expose existence)
        resp = client.delete(
            f"/api/v1/autopilot/personas/{persona_b_id}?company_profile_id={brand_a_id}"
        )
        assert resp.status_code == 404
    app.dependency_overrides.clear()


def test_user_a_cannot_approve_user_b_review_item():
    user_a = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    user_b = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    brand_b_id = str(uuid4())
    review_id = str(uuid4())

    stores = {
        "company_profiles": [{"id": brand_b_id, "user_id": user_b.id}],
        "linkedin_review_queue": [
            {
                "id": review_id,
                "user_id": user_b.id,
                "company_profile_id": brand_b_id,
                "target_post_id": "post_123",
                "comment_text": "Nice post!",
                "status": "pending_review",
            }
        ],
    }
    mock_client = MockSupabaseClient(stores)

    app.dependency_overrides[get_authenticated_user] = lambda: user_a
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        resp = client.post(f"/api/v1/autopilot/review/{review_id}/approve", json={})
        assert resp.status_code == 403
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_brand_a_cannot_use_brand_b_linkedin_account():
    user_a = str(uuid4())
    user_b = str(uuid4())
    acc_b_id = str(uuid4())

    brand_a = {
        "id": str(uuid4()),
        "user_id": user_a,
        "default_linkedin_account_id": acc_b_id,
    }
    account_b = {
        "id": acc_b_id,
        "user_id": user_b,  # Belongs to user B, not user A!
        "status": "connected",
        "unipile_account_id": "unipile_b",
    }
    client = MockSupabaseClient({"linkedin_accounts": [account_b]})

    with pytest.raises(BrandAccountResolutionError, match="does not match brand owner"):
        await resolve_brand_linkedin_account(brand_a, client=client)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SETTINGS PERSISTENCE & ZERO IN-MEMORY FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════


def test_settings_persist_across_client_requests():
    user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    brand_id = str(uuid4())

    stores = {
        "company_profiles": [{"id": brand_id, "user_id": user.id, "company_name": "Test Co"}],
        "linkedin_engagement_settings": [],
    }
    mock_client = MockSupabaseClient(stores)

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        TestClient(app) as client,
    ):
        # 1. Update settings
        put_resp = client.put(
            "/api/v1/autopilot/settings",
            json={
                "company_profile_id": brand_id,
                "engagement_enabled": True,
                "auto_like_enabled": True,
                "likes_per_day": 22,
                "connection_note_template": "Hello {first_name}",
            },
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["likes_per_day"] == 22
        assert put_resp.json()["auto_like_enabled"] is True

        # 2. Re-read settings on fresh GET request
        get_resp = client.get(f"/api/v1/autopilot/settings?company_profile_id={brand_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["likes_per_day"] == 22
        assert get_resp.json()["connection_note_template"] == "Hello {first_name}"
        assert get_resp.json()["engagement_enabled"] is True

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. AUTO LIKES — DURABLE CLAIM, PERMANENT IDEMPOTENCY, TIMEOUT NEEDS_REVIEW
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_auto_likes_dispatches_once_and_prevents_duplicate_run():
    user_id = str(uuid4())
    brand_id = str(uuid4())
    account_id = str(uuid4())
    unipile_id = "mock_unipile_acc"

    stores: dict[str, list[dict[str, Any]]] = {
        "linkedin_engagement_log": [],
        "linkedin_engaged_posts": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)

    mock_gateway = AsyncMock()
    mock_gateway.like_post.return_value = {"status": "ok", "id": "reaction_123"}

    executor = EngagementSessionExecutor(
        brand_id=brand_id,
        user_id=user_id,
        linkedin_account_id=account_id,
        unipile_account_id=unipile_id,
        client=mock_client,
        gateway=mock_gateway,
        rate_limiter=MagicMock(delay_between_actions=AsyncMock(return_value=0.0)),
    )

    target = TargetPost(
        post_id="post_999",
        author_profile_id="author_1",
        author_name="Alice",
        content="Great AI update",
        posted_at=datetime.now(UTC),
        persona_label="AI",
    )

    # 1. First execution -> claim inserted & like dispatched
    res1 = await executor._execute_like(target, current_count=0, max_count=10)
    assert res1 is True
    assert mock_gateway.like_post.call_count == 1
    assert len(stores["linkedin_engagement_log"]) == 1
    assert stores["linkedin_engagement_log"][0]["status"] == "succeeded"

    # 2. Duplicate scheduler run on same target post -> durable claim fails (permanent idempotency)
    # Simulate DB unique index rejecting second claim for same (account_id, target_post_id)
    res2 = await executor._execute_like(target, current_count=1, max_count=10)
    assert res2 is False
    assert mock_gateway.like_post.call_count == 1  # No second external dispatch!


@pytest.mark.asyncio
async def test_auto_likes_timeout_marks_needs_review_and_blocks_retry():
    user_id = str(uuid4())
    brand_id = str(uuid4())
    account_id = str(uuid4())
    unipile_id = "mock_unipile_acc"

    stores: dict[str, list[dict[str, Any]]] = {
        "linkedin_engagement_log": [],
        "linkedin_engaged_posts": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)

    mock_gateway = AsyncMock()
    mock_gateway.like_post.side_effect = TimeoutError("Gateway timeout")

    executor = EngagementSessionExecutor(
        brand_id=brand_id,
        user_id=user_id,
        linkedin_account_id=account_id,
        unipile_account_id=unipile_id,
        client=mock_client,
        gateway=mock_gateway,
        rate_limiter=MagicMock(delay_between_actions=AsyncMock(return_value=0.0)),
    )

    target = TargetPost(
        post_id="post_timeout_1",
        author_profile_id="author_2",
        author_name="Bob",
        content="Test content",
        posted_at=datetime.now(UTC),
        persona_label="Tech",
    )

    res = await executor._execute_like(target, current_count=0, max_count=10)
    assert res is False
    assert len(stores["linkedin_engagement_log"]) == 1
    # Status is needs_review, NEVER retried
    assert stores["linkedin_engagement_log"][0]["status"] == "needs_review"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. AUTO COMMENTS — GENERATION ONLY & 3-PHASE CRASH-SAFE APPROVAL
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_scheduler_never_calls_unipile_comment_during_generation():
    user_id = str(uuid4())
    brand_id = str(uuid4())
    account_id = str(uuid4())

    stores: dict[str, list[dict[str, Any]]] = {
        "linkedin_review_queue": [],
        "linkedin_engagement_log": [],
    }
    mock_client = MockSupabaseClient(stores)
    mock_gateway = AsyncMock()

    executor = EngagementSessionExecutor(
        brand_id=brand_id,
        user_id=user_id,
        linkedin_account_id=account_id,
        unipile_account_id="unipile_acc",
        client=mock_client,
        gateway=mock_gateway,
        rate_limiter=MagicMock(delay_between_actions=AsyncMock(return_value=0.0)),
    )

    target = TargetPost(
        post_id="post_candidate_1",
        author_profile_id="author_3",
        author_name="Charlie",
        content="Building something exciting",
        posted_at=datetime.now(UTC),
        persona_label="Founders",
    )

    with patch(
        "src.modules.linkedin.generators.comment_generator.CommentGenerator.generate_comment",
        return_value="Great insight Charlie!",
    ):
        res = await executor._generate_and_queue_comment(target, current_count=0, max_count=5)

    assert res is True
    # Review queue must contain pending_review item
    assert len(stores["linkedin_review_queue"]) == 1
    assert stores["linkedin_review_queue"][0]["status"] == "pending_review"
    assert stores["linkedin_review_queue"][0]["generated_text"] == "Great insight Charlie!"
    assert "generated_at" in stores["linkedin_review_queue"][0]
    assert "created_at" not in stores["linkedin_review_queue"][0]

    # CRITICAL: External comment write API MUST NOT be called!
    assert mock_gateway.comment_on_post.call_count == 0


def test_approve_generated_comment_without_edit():
    user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    brand_id = str(uuid4())
    account_uuid = str(uuid4())
    review_id = str(uuid4())

    stores = {
        "company_profiles": [{"id": brand_id, "user_id": user.id}],
        "linkedin_accounts": [
            {
                "id": account_uuid,
                "user_id": user.id,
                "status": "connected",
                "unipile_account_id": "unipile_acc_valid",
            }
        ],
        "linkedin_review_queue": [
            {
                "id": review_id,
                "user_id": user.id,
                "company_profile_id": brand_id,
                "linkedin_account_id": account_uuid,
                "target_post_id": "target_p_1",
                "generated_text": "Original AI draft comment",
                "status": "pending_review",
            }
        ],
        "linkedin_engagement_log": [],
        "linkedin_engaged_posts": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)

    mock_gateway = AsyncMock()
    mock_gateway.comment_on_post.return_value = {"id": "cmt_ext_123"}

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        patch("src.api.v1.autopilot.get_unipile_gateway", return_value=mock_gateway),
        TestClient(app) as client,
    ):
        # 1. Approve without edit payload
        resp = client.post(
            f"/api/v1/autopilot/review/{review_id}/approve",
            json={},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

        # Verify Unipile was called with original generated text
        mock_gateway.comment_on_post.assert_awaited_once_with(
            account_id="unipile_acc_valid",
            post_id="target_p_1",
            text="Original AI draft comment",
        )

        # Verify review queue is marked published and preserved generated_text
        assert stores["linkedin_review_queue"][0]["generated_text"] == "Original AI draft comment"
        assert stores["linkedin_review_queue"][0]["status"] == "published"
        assert stores["linkedin_engagement_log"][0]["status"] == "succeeded"
        assert stores["linkedin_engagement_log"][0]["comment_text"] == "Original AI draft comment"

    app.dependency_overrides.clear()


def test_approve_edited_comment():
    user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    brand_id = str(uuid4())
    account_uuid = str(uuid4())
    review_id = str(uuid4())

    stores = {
        "company_profiles": [{"id": brand_id, "user_id": user.id}],
        "linkedin_accounts": [
            {
                "id": account_uuid,
                "user_id": user.id,
                "status": "connected",
                "unipile_account_id": "unipile_acc_valid",
            }
        ],
        "linkedin_review_queue": [
            {
                "id": review_id,
                "user_id": user.id,
                "company_profile_id": brand_id,
                "linkedin_account_id": account_uuid,
                "target_post_id": "target_p_1",
                "generated_text": "Original AI draft comment",
                "status": "pending_review",
            }
        ],
        "linkedin_engagement_log": [],
        "linkedin_engaged_posts": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)

    mock_gateway = AsyncMock()
    mock_gateway.comment_on_post.return_value = {"id": "cmt_ext_123"}

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        patch("src.api.v1.autopilot.get_unipile_gateway", return_value=mock_gateway),
        TestClient(app) as client,
    ):
        # Approve with edited comment text
        resp = client.post(
            f"/api/v1/autopilot/review/{review_id}/approve",
            json={"comment_text": "Polished edited comment text!"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

        # Verify Unipile was called with edited text
        mock_gateway.comment_on_post.assert_awaited_once_with(
            account_id="unipile_acc_valid",
            post_id="target_p_1",
            text="Polished edited comment text!",
        )

        # Verify review queue updated generated_text
        assert (
            stores["linkedin_review_queue"][0]["generated_text"] == "Polished edited comment text!"
        )
        assert stores["linkedin_review_queue"][0]["status"] == "published"
        assert stores["linkedin_engagement_log"][0]["status"] == "succeeded"
        assert (
            stores["linkedin_engagement_log"][0]["comment_text"] == "Polished edited comment text!"
        )

    app.dependency_overrides.clear()


def test_double_approval_sends_once():
    user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    brand_id = str(uuid4())
    account_uuid = str(uuid4())
    review_id = str(uuid4())

    stores = {
        "company_profiles": [{"id": brand_id, "user_id": user.id}],
        "linkedin_accounts": [
            {
                "id": account_uuid,
                "user_id": user.id,
                "status": "connected",
                "unipile_account_id": "unipile_acc_valid",
            }
        ],
        "linkedin_review_queue": [
            {
                "id": review_id,
                "user_id": user.id,
                "company_profile_id": brand_id,
                "linkedin_account_id": account_uuid,
                "target_post_id": "target_p_1",
                "generated_text": "Original AI draft comment",
                "status": "pending_review",
            }
        ],
        "linkedin_engagement_log": [],
        "linkedin_engaged_posts": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)

    mock_gateway = AsyncMock()
    mock_gateway.comment_on_post.return_value = {"id": "cmt_ext_123"}

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        patch("src.api.v1.autopilot.get_unipile_gateway", return_value=mock_gateway),
        TestClient(app) as client,
    ):
        # 1. First approval
        first_resp = client.post(
            f"/api/v1/autopilot/review/{review_id}/approve",
            json={"comment_text": "Approved comment"},
        )
        assert first_resp.status_code == 200

        # 2. Second approval must fail closed with 409
        second_resp = client.post(
            f"/api/v1/autopilot/review/{review_id}/approve",
            json={"comment_text": "Approved comment again"},
        )
        assert second_resp.status_code == 409
        # Crucial: Unipile dispatch happened exactly once
        assert mock_gateway.comment_on_post.call_count == 1

    app.dependency_overrides.clear()


def test_comment_approval_timeout_marks_needs_review_no_retry():
    user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    brand_id = str(uuid4())
    account_uuid = str(uuid4())
    review_id = str(uuid4())

    stores = {
        "company_profiles": [{"id": brand_id, "user_id": user.id}],
        "linkedin_accounts": [
            {
                "id": account_uuid,
                "user_id": user.id,
                "status": "connected",
                "unipile_account_id": "unipile_acc_valid",
            }
        ],
        "linkedin_review_queue": [
            {
                "id": review_id,
                "user_id": user.id,
                "company_profile_id": brand_id,
                "linkedin_account_id": account_uuid,
                "target_post_id": "target_p_1",
                "generated_text": "Original AI draft comment",
                "status": "pending_review",
            }
        ],
        "linkedin_engagement_log": [],
        "linkedin_engaged_posts": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)

    mock_gateway = AsyncMock()
    mock_gateway.comment_on_post.side_effect = httpx.TimeoutException("Read timeout from Unipile")

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        patch("src.api.v1.autopilot.get_unipile_gateway", return_value=mock_gateway),
        TestClient(app) as client,
    ):
        resp = client.post(
            f"/api/v1/autopilot/review/{review_id}/approve",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["status"] == "needs_review"
        assert "Timeout" in data["error"]

        # Exactly 1 call was attempted (never auto-retried)
        assert mock_gateway.comment_on_post.call_count == 1

        # Both review queue and engagement log transitioned to needs_review
        assert stores["linkedin_review_queue"][0]["status"] == "needs_review"
        assert stores["linkedin_engagement_log"][0]["status"] == "needs_review"

    app.dependency_overrides.clear()


def test_comment_approval_successful_send_str_and_dict():
    user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    brand_id = str(uuid4())
    account_uuid = str(uuid4())

    # Case A: String return from gateway (standard UnipileGateway behavior)
    review_id_a = str(uuid4())
    stores = {
        "company_profiles": [{"id": brand_id, "user_id": user.id}],
        "linkedin_accounts": [
            {
                "id": account_uuid,
                "user_id": user.id,
                "status": "connected",
                "unipile_account_id": "unipile_acc_valid",
            }
        ],
        "linkedin_review_queue": [
            {
                "id": review_id_a,
                "user_id": user.id,
                "company_profile_id": brand_id,
                "linkedin_account_id": account_uuid,
                "target_post_id": "target_p_a",
                "generated_text": "Draft A",
                "status": "pending_review",
            }
        ],
        "linkedin_engagement_log": [],
        "linkedin_engaged_posts": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)
    mock_gateway = AsyncMock()
    mock_gateway.comment_on_post.return_value = "cmt_ext_str_789"

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        patch("src.api.v1.autopilot.get_unipile_gateway", return_value=mock_gateway),
        TestClient(app) as client,
    ):
        resp_a = client.post(f"/api/v1/autopilot/review/{review_id_a}/approve", json={})
        assert resp_a.status_code == 200
        assert resp_a.json()["status"] == "published"
        assert resp_a.json()["provider_result_id"] == "cmt_ext_str_789"
        assert stores["linkedin_review_queue"][0]["status"] == "published"
        assert stores["linkedin_engagement_log"][0]["status"] == "succeeded"

    # Case B: Dict return from gateway
    review_id_b = str(uuid4())
    stores["linkedin_review_queue"].append(
        {
            "id": review_id_b,
            "user_id": user.id,
            "company_profile_id": brand_id,
            "linkedin_account_id": account_uuid,
            "target_post_id": "target_p_b",
            "generated_text": "Draft B",
            "status": "pending_review",
        }
    )
    mock_gateway.comment_on_post.return_value = {"comment_id": "cmt_ext_dict_456"}
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        patch("src.api.v1.autopilot.get_unipile_gateway", return_value=mock_gateway),
        TestClient(app) as client,
    ):
        resp_b = client.post(f"/api/v1/autopilot/review/{review_id_b}/approve", json={})
        assert resp_b.status_code == 200
        assert resp_b.json()["status"] == "published"
        assert resp_b.json()["provider_result_id"] == "cmt_ext_dict_456"

    app.dependency_overrides.clear()


def test_comment_approval_definitive_rejection_marks_failed():
    user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    brand_id = str(uuid4())
    account_uuid = str(uuid4())
    review_id = str(uuid4())

    stores = {
        "company_profiles": [{"id": brand_id, "user_id": user.id}],
        "linkedin_accounts": [
            {
                "id": account_uuid,
                "user_id": user.id,
                "status": "connected",
                "unipile_account_id": "unipile_acc_valid",
            }
        ],
        "linkedin_review_queue": [
            {
                "id": review_id,
                "user_id": user.id,
                "company_profile_id": brand_id,
                "linkedin_account_id": account_uuid,
                "target_post_id": "target_p_1",
                "generated_text": "Original AI draft comment",
                "status": "pending_review",
            }
        ],
        "linkedin_engagement_log": [],
        "linkedin_engaged_posts": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)

    mock_gateway = AsyncMock()
    req = httpx.Request("POST", "https://api.unipile.com/api/v1/posts/p1/comments")
    resp = httpx.Response(status_code=403, request=req, text="Forbidden action")
    mock_gateway.comment_on_post.side_effect = httpx.HTTPStatusError(
        "Forbidden", request=req, response=resp
    )

    app.dependency_overrides[get_authenticated_user] = lambda: user
    with (
        patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        patch("src.repositories.base.get_supabase_client", return_value=mock_client),
        patch("src.api.v1.autopilot.get_unipile_gateway", return_value=mock_gateway),
        TestClient(app) as client,
    ):
        res = client.post(f"/api/v1/autopilot/review/{review_id}/approve", json={})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        assert data["status"] == "failed"

        assert stores["linkedin_review_queue"][0]["status"] == "failed"
        assert stores["linkedin_engagement_log"][0]["status"] == "failed"

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 6. AUTO CONNECTIONS — RELATION CHECKS & PERMANENT IDEMPOTENCY
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_auto_connection_empty_or_none_note_does_not_crash():
    """Proves empty or None connection note does not crash with AttributeError and dispatches safely."""
    user_id = str(uuid4())
    brand_id = str(uuid4())
    account_id = str(uuid4())

    stores: dict[str, list[dict[str, Any]]] = {
        "linkedin_engagement_log": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)
    mock_gateway = AsyncMock()
    mock_gateway.check_relation.return_value = {"status": "NOT_CONNECTED"}
    mock_gateway.send_connection_request.return_value = {"id": "inv_none_note_123"}

    # Executor with empty connection_note_template
    executor = EngagementSessionExecutor(
        brand_id=brand_id,
        user_id=user_id,
        linkedin_account_id=account_id,
        unipile_account_id="unipile_acc",
        connection_note_template="",
        client=mock_client,
        gateway=mock_gateway,
        rate_limiter=MagicMock(delay_between_actions=AsyncMock(return_value=0.0)),
    )

    from src.modules.linkedin.models import ResolvedTarget

    target_prof = ResolvedTarget(
        account_id=account_id,
        persona_label="Engineers",
        profile_id="prof_none_note",
    )

    # Dispatches with note=None without any crash
    res = await executor._execute_connection(target_prof, current_count=0, max_count=10)
    assert res is True
    mock_gateway.send_connection_request.assert_awaited_once_with(
        "unipile_acc", "prof_none_note", None
    )
    assert len(stores["linkedin_engagement_log"]) == 1
    assert stores["linkedin_engagement_log"][0]["status"] == "succeeded"
    assert stores["linkedin_engagement_log"][0]["provider_result_id"] == "inv_none_note_123"


@pytest.mark.asyncio
async def test_auto_connection_skips_already_connected_or_pending():
    """Proves connected or pending profiles are skipped before dispatch."""
    user_id = str(uuid4())
    brand_id = str(uuid4())
    account_id = str(uuid4())

    stores: dict[str, list[dict[str, Any]]] = {
        "linkedin_engagement_log": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)
    mock_gateway = AsyncMock()

    executor = EngagementSessionExecutor(
        brand_id=brand_id,
        user_id=user_id,
        linkedin_account_id=account_id,
        unipile_account_id="unipile_acc",
        client=mock_client,
        gateway=mock_gateway,
        rate_limiter=MagicMock(delay_between_actions=AsyncMock(return_value=0.0)),
    )

    from src.modules.linkedin.models import ResolvedTarget

    target_prof = ResolvedTarget(
        account_id=account_id,
        persona_label="SaaS",
        profile_id="prof_already_connected",
    )

    # 1. Gateway reports already CONNECTED -> skipped, zero calls, zero claims
    mock_gateway.check_relation.return_value = {"status": "CONNECTED"}
    res1 = await executor._execute_connection(target_prof, current_count=0, max_count=10)
    assert res1 is False
    assert mock_gateway.send_connection_request.call_count == 0
    assert len(stores["linkedin_engagement_log"]) == 0

    # 2. Gateway reports PENDING invite -> skipped, zero calls, zero claims
    mock_gateway.check_relation.return_value = {"status": "PENDING"}
    res2 = await executor._execute_connection(target_prof, current_count=0, max_count=10)
    assert res2 is False
    assert mock_gateway.send_connection_request.call_count == 0
    assert len(stores["linkedin_engagement_log"]) == 0

    # 3. Not connected -> dispatches invite once
    mock_gateway.check_relation.return_value = {"status": "NOT_CONNECTED"}
    mock_gateway.send_connection_request.return_value = {"id": "inv_123"}
    res3 = await executor._execute_connection(target_prof, current_count=0, max_count=10)
    assert res3 is True
    assert mock_gateway.send_connection_request.call_count == 1
    assert stores["linkedin_engagement_log"][0]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_auto_connection_timeout_marks_needs_review_no_retry():
    """Proves timeout or ambiguous outcome marks claim needs_review and blocks retry."""
    user_id = str(uuid4())
    brand_id = str(uuid4())
    account_id = str(uuid4())

    stores: dict[str, list[dict[str, Any]]] = {
        "linkedin_engagement_log": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)
    mock_gateway = AsyncMock()
    mock_gateway.check_relation.return_value = {"status": "NOT_CONNECTED"}
    mock_gateway.send_connection_request.side_effect = httpx.TimeoutException(
        "Read timeout on invite dispatch"
    )

    executor = EngagementSessionExecutor(
        brand_id=brand_id,
        user_id=user_id,
        linkedin_account_id=account_id,
        unipile_account_id="unipile_acc",
        client=mock_client,
        gateway=mock_gateway,
        rate_limiter=MagicMock(delay_between_actions=AsyncMock(return_value=0.0)),
    )

    from src.modules.linkedin.models import ResolvedTarget

    target_prof = ResolvedTarget(
        account_id=account_id,
        persona_label="SaaS",
        profile_id="prof_timeout_target",
    )

    res = await executor._execute_connection(target_prof, current_count=0, max_count=10)
    assert res is False
    assert mock_gateway.send_connection_request.call_count == 1

    # Claim must be in needs_review, preserving timeout error
    assert len(stores["linkedin_engagement_log"]) == 1
    log_row = stores["linkedin_engagement_log"][0]
    assert log_row["status"] == "needs_review"
    assert "Timeout" in log_row["error_message"]

    # Second attempt must be rejected by dedupe and NEVER auto-retried
    mock_gateway.send_connection_request.reset_mock()
    res_retry = await executor._execute_connection(target_prof, current_count=0, max_count=10)
    assert res_retry is False
    mock_gateway.send_connection_request.assert_not_called()


@pytest.mark.asyncio
async def test_auto_connection_double_run_never_sends_twice():
    """Proves duplicate execution for the same target profile is permanently deduplicated."""
    user_id = str(uuid4())
    brand_id = str(uuid4())
    account_id = str(uuid4())

    stores: dict[str, list[dict[str, Any]]] = {
        "linkedin_engagement_log": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)
    mock_gateway = AsyncMock()
    mock_gateway.check_relation.return_value = {"status": "NOT_CONNECTED"}
    mock_gateway.send_connection_request.return_value = "invite_sent_999"

    executor = EngagementSessionExecutor(
        brand_id=brand_id,
        user_id=user_id,
        linkedin_account_id=account_id,
        unipile_account_id="unipile_acc",
        client=mock_client,
        gateway=mock_gateway,
        rate_limiter=MagicMock(delay_between_actions=AsyncMock(return_value=0.0)),
    )

    from src.modules.linkedin.models import ResolvedTarget

    target = ResolvedTarget(
        account_id=account_id,
        persona_label="Founders",
        profile_id="prof_once_only",
    )

    # First run succeeds
    first_ok = await executor._execute_connection(target, current_count=0, max_count=10)
    assert first_ok is True
    assert mock_gateway.send_connection_request.call_count == 1
    assert stores["linkedin_engagement_log"][0]["status"] == "succeeded"

    # Second run immediately skips due to existing log
    second_ok = await executor._execute_connection(target, current_count=1, max_count=10)
    assert second_ok is False
    assert mock_gateway.send_connection_request.call_count == 1


@pytest.mark.asyncio
async def test_auto_connection_successful_invite_marks_succeeded():
    """Proves successful invite dispatch records status succeeded and provider_result_id."""
    user_id = str(uuid4())
    brand_id = str(uuid4())
    account_id = str(uuid4())

    stores: dict[str, list[dict[str, Any]]] = {
        "linkedin_engagement_log": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)
    mock_gateway = AsyncMock()
    mock_gateway.check_relation.return_value = {"status": "NOT_CONNECTED"}
    mock_gateway.send_connection_request.return_value = {"id": "unipile_inv_777"}

    executor = EngagementSessionExecutor(
        brand_id=brand_id,
        user_id=user_id,
        linkedin_account_id=account_id,
        unipile_account_id="unipile_acc",
        client=mock_client,
        gateway=mock_gateway,
        rate_limiter=MagicMock(delay_between_actions=AsyncMock(return_value=0.0)),
    )

    from src.modules.linkedin.models import ResolvedTarget

    target = ResolvedTarget(
        account_id=account_id,
        persona_label="Founders",
        profile_id="prof_success_1",
    )

    ok = await executor._execute_connection(target, current_count=0, max_count=10)
    assert ok is True
    assert len(stores["linkedin_engagement_log"]) == 1
    assert stores["linkedin_engagement_log"][0]["status"] == "succeeded"
    assert stores["linkedin_engagement_log"][0]["provider_result_id"] == "unipile_inv_777"


@pytest.mark.asyncio
async def test_auto_connection_4xx_rejection_marks_failed():
    """Proves definitive 4xx HTTP client rejection marks claim failed."""
    user_id = str(uuid4())
    brand_id = str(uuid4())
    account_id = str(uuid4())

    stores: dict[str, list[dict[str, Any]]] = {
        "linkedin_engagement_log": [],
        "linkedin_daily_actions": [],
    }
    mock_client = MockSupabaseClient(stores)
    mock_gateway = AsyncMock()
    mock_gateway.check_relation.return_value = {"status": "NOT_CONNECTED"}

    req = httpx.Request("POST", "https://api.unipile.com/api/v1/users/invite")
    resp = httpx.Response(
        status_code=400,
        request=req,
        text='{"error": "CANNOT_INVITE", "message": "Cannot invite this user"}',
    )
    mock_gateway.send_connection_request.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=req, response=resp
    )

    executor = EngagementSessionExecutor(
        brand_id=brand_id,
        user_id=user_id,
        linkedin_account_id=account_id,
        unipile_account_id="unipile_acc",
        client=mock_client,
        gateway=mock_gateway,
        rate_limiter=MagicMock(delay_between_actions=AsyncMock(return_value=0.0)),
    )

    from src.modules.linkedin.models import ResolvedTarget

    target = ResolvedTarget(
        account_id=account_id,
        persona_label="Founders",
        profile_id="prof_400_fail",
    )

    ok = await executor._execute_connection(target, current_count=0, max_count=10)
    assert ok is False
    assert len(stores["linkedin_engagement_log"]) == 1
    assert stores["linkedin_engagement_log"][0]["status"] == "failed"
    assert "HTTP 400" in stores["linkedin_engagement_log"][0]["error_message"]


@pytest.mark.asyncio
async def test_unipile_gateway_send_connection_request_note_handling():
    """Directly verifies UnipileGateway.send_connection_request payload and error handling."""
    from src.gateways.unipile_gateway import UnipileGateway

    gateway = UnipileGateway(dsn="https://api.unipile.com", token="dummy_token")

    # Case 1: message is None -> no message key in payload
    with patch("httpx.AsyncClient.post") as mock_post:
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"id": "inv_none"}
        mock_post.return_value = resp

        res = await gateway.send_connection_request("acc_1", "prof_1", message=None)
        assert res == "inv_none"
        sent_payload = mock_post.call_args[1]["json"]
        assert "message" not in sent_payload
        assert sent_payload["account_id"] == "acc_1"
        assert sent_payload["provider_id"] == "prof_1"

    # Case 2: message provided -> included in payload
    with patch("httpx.AsyncClient.post") as mock_post:
        resp = MagicMock(status_code=201)
        resp.json.return_value = {"invite_id": "inv_custom"}
        mock_post.return_value = resp

        res = await gateway.send_connection_request("acc_1", "prof_1", message="Hi there!")
        assert res == "inv_custom"
        sent_payload = mock_post.call_args[1]["json"]
        assert sent_payload["message"] == "Hi there!"

    # Case 3: timeout is re-raised
    with (
        patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout")),
        pytest.raises(httpx.TimeoutException),
    ):
        await gateway.send_connection_request("acc_1", "prof_1", message=None)


@pytest.mark.asyncio
async def test_unipile_gateway_check_relation_verified_routes():
    """Directly verifies UnipileGateway.check_relation returns CONNECTED, PENDING, or NOT_CONNECTED."""
    from src.gateways.unipile_gateway import UnipileGateway

    gateway = UnipileGateway(dsn="https://api.unipile.com", token="dummy_token")

    # 1. Profile returns FIRST_DEGREE
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: {"network_distance": "FIRST_DEGREE"}
        )
        res = await gateway.check_relation("acc_1", "target_connected")
        assert res["status"] == "CONNECTED"

    # 2. Profile returns is_relationship=True
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"is_relationship": True})
        res = await gateway.check_relation("acc_1", "target_rel")
        assert res["status"] == "CONNECTED"

    # 3. Target profile found in sent invitations list
    def mock_get_router(url, *args, **kwargs):
        if "invite/sent" in url:
            return MagicMock(
                status_code=200,
                json=lambda: {
                    "object": "InvitationList",
                    "items": [{"id": "inv_99", "invited_user_id": "target_pending"}],
                },
            )
        return MagicMock(
            status_code=200,
            json=lambda: {"network_distance": "SECOND_DEGREE", "is_relationship": False},
        )

    with patch("httpx.AsyncClient.get", side_effect=mock_get_router):
        res = await gateway.check_relation("acc_1", "target_pending")
        assert res["status"] == "PENDING"

    # 4. Neither connected nor pending
    def mock_get_neither(url, *args, **kwargs):
        if "invite/sent" in url:
            return MagicMock(status_code=200, json=lambda: {"items": []})
        return MagicMock(
            status_code=200,
            json=lambda: {"network_distance": "THIRD_DEGREE", "is_relationship": False},
        )

    with patch("httpx.AsyncClient.get", side_effect=mock_get_neither):
        res = await gateway.check_relation("acc_1", "target_other")
        assert res["status"] == "NOT_CONNECTED"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. MULTI-TENANT SCHEDULER & ADVISORY LOCKING
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_session_advisory_lock_mutual_exclusion():
    brand_a_id = str(uuid4())
    lock1 = BrandAdvisoryLock(brand_a_id, allow_in_memory=True)
    lock2 = BrandAdvisoryLock(brand_a_id, allow_in_memory=True)

    with patch.object(settings, "DATABASE_URL", None):
        # First worker acquires lock
        acquired1 = await lock1.acquire()
        assert acquired1 is True

        # Overlapping worker for SAME brand cannot acquire lock
        acquired2 = await lock2.acquire()
        assert acquired2 is False

        # First worker releases lock in finally block
        await lock1.release()

        # Now second worker can acquire
        acquired2_retry = await lock2.acquire()
        assert acquired2_retry is True
        await lock2.release()
