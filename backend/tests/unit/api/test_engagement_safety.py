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
            records = [self._insert_data] if isinstance(self._insert_data, dict) else self._insert_data
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
        Path(__file__).resolve().parents[3]
        / "migrations"
        / "025_create_engagement_settings_and_logs.up.sql"
    ).read_text(encoding="utf-8").lower()

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
        Path(__file__).resolve().parents[3]
        / "migrations"
        / "026_scope_personas_and_review_queue.up.sql"
    ).read_text(encoding="utf-8").lower()

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
        "company_profiles": [
            {"id": brand_b_id, "user_id": user_b.id, "company_name": "Brand B"}
        ],
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
        resp = client.delete(f"/api/v1/autopilot/personas/{persona_b_id}?company_profile_id={brand_a_id}")
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

    with patch("src.modules.linkedin.generators.comment_generator.CommentGenerator.generate_comment", return_value="Great insight Charlie!"):
        res = await executor._generate_and_queue_comment(target, current_count=0, max_count=5)

    assert res is True
    # Review queue must contain pending_review item
    assert len(stores["linkedin_review_queue"]) == 1
    assert stores["linkedin_review_queue"][0]["status"] == "pending_review"
    assert stores["linkedin_review_queue"][0].get("generated_text", stores["linkedin_review_queue"][0].get("comment_text")) == "Great insight Charlie!"

    # CRITICAL: External comment write API MUST NOT be called!
    assert mock_gateway.comment_on_post.call_count == 0


def test_crash_safe_comment_approval_flow():
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
                "comment_text": "Draft comment text",
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
        # 1. Approve with edited comment text
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

        # Verify review queue is marked published
        assert stores["linkedin_review_queue"][0]["status"] == "published"
        # Verify engagement log succeeded
        assert stores["linkedin_engagement_log"][0]["status"] == "succeeded"

        # 2. Double approval cannot double send
        second_resp = client.post(
            f"/api/v1/autopilot/review/{review_id}/approve",
            json={"comment_text": "Another try"},
        )
        assert second_resp.status_code == 409  # Conflict! Not in pending_review
        assert mock_gateway.comment_on_post.call_count == 1  # Still only 1 call!

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 6. AUTO CONNECTIONS — RELATION CHECKS & PERMANENT IDEMPOTENCY
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_auto_connection_skips_already_connected_or_pending():
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

    # 1. Gateway reports already CONNECTED
    mock_gateway.check_relation.return_value = {"status": "CONNECTED"}
    res1 = await executor._execute_connection(target_prof, current_count=0, max_count=10)
    assert res1 is False
    assert mock_gateway.send_connection_request.call_count == 0

    # 2. Gateway reports PENDING invite
    mock_gateway.check_relation.return_value = {"status": "PENDING"}
    res2 = await executor._execute_connection(target_prof, current_count=0, max_count=10)
    assert res2 is False
    assert mock_gateway.send_connection_request.call_count == 0

    # 3. Not connected -> dispatches invite once
    mock_gateway.check_relation.return_value = {"status": "NOT_CONNECTED"}
    mock_gateway.send_connection_request.return_value = {"id": "inv_123"}
    res3 = await executor._execute_connection(target_prof, current_count=0, max_count=10)
    assert res3 is True
    assert mock_gateway.send_connection_request.call_count == 1
    assert stores["linkedin_engagement_log"][0]["status"] == "succeeded"


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

