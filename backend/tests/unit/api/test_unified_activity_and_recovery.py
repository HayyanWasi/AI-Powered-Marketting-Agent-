"""Unit tests for Phase F2 — Unified Activity API & Stale-State Recovery.

Covers:
1. Publishing Stale Recovery (F2.1):
   - publishing_started_at NULL -> needs_review
   - old publishing_started_at -> needs_review
   - fresh publishing remains untouched
   - never returns to scheduled
   - late normal completion cannot overwrite needs_review (CAS protection)

2. Engagement Stale Recovery (F2.2):
   - stale claimed -> needs_review
   - fresh claimed untouched
   - succeeded/failed untouched
   - permanent dedupe preserved
   - late worker completion cannot overwrite needs_review (CAS protection)

3. Unified Activity API (F2.3):
   - engagement + publishing merged
   - timestamp ordering (newest first)
   - all filters (source_type, action_type, status, date)
   - pagination (limit, offset, exact total, has_more)
   - User A cannot see User B publishing
   - User A cannot see User B engagement
   - company_profile ownership validation (404 on unowned brand)
   - sanitized error messages in unified response
   - legacy /activity contract remains unchanged
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.dependencies import AuthenticatedUser
from src.api.v1.autopilot import (
    get_engagement_activity,
    get_unified_activity,
)
from src.modules.linkedin.models import EngagementLogStatus, PostStatus
from src.modules.linkedin.worker.engagement_recovery import recover_stale_engagement_claims
from src.modules.linkedin.worker.post_publisher import (
    _mark_failed,
    _mark_needs_review,
    _mark_published,
    execute_post_publish,
    recover_stale_publishing,
)
from src.modules.linkedin.worker.session_executor import SessionExecutor

# ═══════════════════════════════════════════════════════════════════════════════
# 1. PUBLISHING STALE RECOVERY (F2.1)
# ═══════════════════════════════════════════════════════════════════════════════


class TestPublishingStaleRecovery:
    """Verify fail-closed recovery and CAS safety for publishing claims."""

    def test_null_publishing_started_at_recovers_to_needs_review(self) -> None:
        """status='publishing' with NULL publishing_started_at must be moved to needs_review."""
        post_id = str(uuid4())
        mock_repo = MagicMock()
        mock_table = MagicMock()
        mock_repo.client.table.return_value = mock_table

        # Candidate query returns 1 row with started_at=None
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq_status = MagicMock()
        mock_select.eq.return_value = mock_eq_status
        mock_limit = MagicMock()
        mock_eq_status.limit.return_value = mock_limit
        mock_limit.execute.return_value = MagicMock(
            data=[{"id": post_id, "publishing_started_at": None}]
        )

        # CAS Update query
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq_id = MagicMock()
        mock_update.eq.return_value = mock_eq_id
        mock_eq_cas_status = MagicMock()
        mock_eq_id.eq.return_value = mock_eq_cas_status
        mock_is_null = MagicMock()
        mock_eq_cas_status.is_.return_value = mock_is_null
        mock_is_null.execute.return_value = MagicMock(data=[{"id": post_id}])

        recovered = recover_stale_publishing(repo=mock_repo, force=True)

        assert recovered == 1
        # Verify status set to needs_review, never scheduled
        mock_table.update.assert_called_with({"status": PostStatus.NEEDS_REVIEW.value})
        mock_eq_cas_status.is_.assert_called_with("publishing_started_at", "null")

    def test_old_publishing_started_at_recovers_to_needs_review(self) -> None:
        """status='publishing' with old timestamp must be moved to needs_review."""
        post_id = str(uuid4())
        old_time = (datetime.now(UTC) - timedelta(minutes=45)).isoformat()

        mock_repo = MagicMock()
        mock_table = MagicMock()
        mock_repo.client.table.return_value = mock_table

        # Candidate query
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq_status = MagicMock()
        mock_select.eq.return_value = mock_eq_status
        mock_limit = MagicMock()
        mock_eq_status.limit.return_value = mock_limit
        mock_limit.execute.return_value = MagicMock(
            data=[{"id": post_id, "publishing_started_at": old_time}]
        )

        # CAS Update query
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq_id = MagicMock()
        mock_update.eq.return_value = mock_eq_id
        mock_eq_cas_status = MagicMock()
        mock_eq_id.eq.return_value = mock_eq_cas_status
        mock_eq_timestamp = MagicMock()
        mock_eq_cas_status.eq.return_value = mock_eq_timestamp
        mock_eq_timestamp.execute.return_value = MagicMock(data=[{"id": post_id}])

        recovered = recover_stale_publishing(repo=mock_repo, force=True)

        assert recovered == 1
        mock_table.update.assert_called_with({"status": PostStatus.NEEDS_REVIEW.value})
        mock_eq_cas_status.eq.assert_called_with("publishing_started_at", old_time)

    def test_fresh_publishing_claim_untouched(self) -> None:
        """status='publishing' with fresh timestamp (<15m) must remain untouched."""
        post_id = str(uuid4())
        fresh_time = (datetime.now(UTC) - timedelta(minutes=2)).isoformat()

        mock_repo = MagicMock()
        mock_table = MagicMock()
        mock_repo.client.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq_status = MagicMock()
        mock_select.eq.return_value = mock_eq_status
        mock_limit = MagicMock()
        mock_eq_status.limit.return_value = mock_limit
        mock_limit.execute.return_value = MagicMock(
            data=[{"id": post_id, "publishing_started_at": fresh_time}]
        )

        recovered = recover_stale_publishing(repo=mock_repo, force=True)

        assert recovered == 0
        mock_table.update.assert_not_called()

    def test_stale_recovery_never_returns_to_scheduled(self) -> None:
        """Stale recovery must NEVER transition rows to 'scheduled'."""
        post_id = str(uuid4())
        mock_repo = MagicMock()
        mock_table = MagicMock()
        mock_repo.client.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq_status = MagicMock()
        mock_select.eq.return_value = mock_eq_status
        mock_limit = MagicMock()
        mock_eq_status.limit.return_value = mock_limit
        mock_limit.execute.return_value = MagicMock(
            data=[{"id": post_id, "publishing_started_at": None}]
        )

        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq_id = MagicMock()
        mock_update.eq.return_value = mock_eq_id
        mock_eq_cas_status = MagicMock()
        mock_eq_id.eq.return_value = mock_eq_cas_status
        mock_is_null = MagicMock()
        mock_eq_cas_status.is_.return_value = mock_is_null
        mock_is_null.execute.return_value = MagicMock(data=[{"id": post_id}])

        recover_stale_publishing(repo=mock_repo, force=True)

        # Confirm update payload has status = 'needs_review' and NOT 'scheduled'
        update_call = mock_table.update.call_args[0][0]
        assert update_call.get("status") == PostStatus.NEEDS_REVIEW.value
        assert update_call.get("status") != PostStatus.SCHEDULED.value

    def test_late_worker_mark_published_cannot_overwrite_needs_review(self) -> None:
        """_mark_published must include .eq('status', 'publishing') CAS guard."""
        post_id = str(uuid4())
        mock_repo = MagicMock()
        mock_table = MagicMock()
        mock_repo.client.table.return_value = mock_table

        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq_id = MagicMock()
        mock_update.eq.return_value = mock_eq_id
        mock_eq_status = MagicMock()
        mock_eq_id.eq.return_value = mock_eq_status

        _mark_published(mock_repo, post_id, "unipile-123")

        mock_update.eq.assert_called_with("id", post_id)
        mock_eq_id.eq.assert_called_with("status", PostStatus.PUBLISHING.value)

    def test_late_worker_mark_failed_cannot_overwrite_needs_review(self) -> None:
        """_mark_failed must include .eq('status', 'publishing') CAS guard."""
        post_id = str(uuid4())
        mock_repo = MagicMock()
        mock_table = MagicMock()
        mock_repo.client.table.return_value = mock_table

        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq_id = MagicMock()
        mock_update.eq.return_value = mock_eq_id
        mock_eq_status = MagicMock()
        mock_eq_id.eq.return_value = mock_eq_status

        _mark_failed(mock_repo, post_id, "Some failure")

        mock_update.eq.assert_called_with("id", post_id)
        mock_eq_id.eq.assert_called_with("status", PostStatus.PUBLISHING.value)

    def test_late_worker_mark_needs_review_cannot_overwrite_other_statuses(self) -> None:
        """_mark_needs_review must include .eq('status', 'publishing') CAS guard."""
        post_id = str(uuid4())
        mock_repo = MagicMock()
        mock_table = MagicMock()
        mock_repo.client.table.return_value = mock_table

        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq_id = MagicMock()
        mock_update.eq.return_value = mock_eq_id
        mock_eq_status = MagicMock()
        mock_eq_id.eq.return_value = mock_eq_status

        _mark_needs_review(mock_repo, post_id, "Timeout")

        mock_update.eq.assert_called_with("id", post_id)
        mock_eq_id.eq.assert_called_with("status", PostStatus.PUBLISHING.value)

    @pytest.mark.asyncio
    async def test_execute_post_publish_cas_rejects_late_completion(self) -> None:
        """If remote dispatch succeeds late but row was moved to needs_review, CAS rejects overwrite."""
        post_id = str(uuid4())
        mock_repo = MagicMock()
        mock_table = MagicMock()
        mock_repo.client.table.return_value = mock_table

        # CAS update returns 0 rows modified (because row is no longer in 'publishing')
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq_id = MagicMock()
        mock_update.eq.return_value = mock_eq_id
        mock_eq_status = MagicMock()
        mock_eq_id.eq.return_value = mock_eq_status
        mock_eq_status.execute.return_value = MagicMock(data=[])  # 0 rows updated

        mock_gateway = AsyncMock()
        mock_gateway.create_post.return_value = "unipile-post-late-999"

        result = await execute_post_publish(
            repo=mock_repo,
            gateway=mock_gateway,
            post_id=post_id,
            account_id=str(uuid4()),
            full_content="Hello LinkedIn!",
        )

        assert result["status"] == PostStatus.NEEDS_REVIEW.value
        assert result["success"] is False
        assert "late worker" in result["error"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ENGAGEMENT STALE RECOVERY (F2.2)
# ═══════════════════════════════════════════════════════════════════════════════


class TestEngagementStaleRecovery:
    """Verify fail-closed recovery and CAS safety for engagement claims."""

    def test_stale_claimed_moves_to_needs_review(self) -> None:
        """claimed log older than threshold must be transitioned to needs_review."""
        claim_id = str(uuid4())
        old_time = (datetime.now(UTC) - timedelta(minutes=20)).isoformat()

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # Select stale claimed rows
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq_status = MagicMock()
        mock_select.eq.return_value = mock_eq_status
        mock_lte = MagicMock()
        mock_eq_status.lte.return_value = mock_lte
        mock_limit = MagicMock()
        mock_lte.limit.return_value = mock_limit
        mock_limit.execute.return_value = MagicMock(
            data=[{"id": claim_id, "created_at": old_time, "action_type": "like"}]
        )

        # CAS Update
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq_id = MagicMock()
        mock_update.eq.return_value = mock_eq_id
        mock_eq_cas_status = MagicMock()
        mock_eq_id.eq.return_value = mock_eq_cas_status
        mock_eq_cas_status.execute.return_value = MagicMock(data=[{"id": claim_id}])

        recovered = recover_stale_engagement_claims(
            client=mock_client, stale_minutes=15, force=True
        )

        assert recovered == 1
        update_payload = mock_table.update.call_args[0][0]
        assert update_payload.get("status") == EngagementLogStatus.NEEDS_REVIEW.value
        assert "Stale claim: worker interrupted before completion" in update_payload.get(
            "error_message"
        )
        assert "completed_at" in update_payload
        mock_eq_cas_status.execute.assert_called()

    def test_fresh_claimed_engagement_untouched(self) -> None:
        """claimed log under threshold (<15m) must remain untouched."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq_status = MagicMock()
        mock_select.eq.return_value = mock_eq_status
        mock_lte = MagicMock()
        mock_eq_status.lte.return_value = mock_lte
        mock_limit = MagicMock()
        mock_lte.limit.return_value = mock_limit
        # Query with lte(now - 15m) returns empty list
        mock_limit.execute.return_value = MagicMock(data=[])

        recovered = recover_stale_engagement_claims(
            client=mock_client, stale_minutes=15, force=True
        )

        assert recovered == 0
        mock_table.update.assert_not_called()

    def test_permanent_dedupe_preserved_on_recovery(self) -> None:
        """Stale recovery keeps row in DB (never deletes) preserving permanent unique dedupe."""
        claim_id = str(uuid4())
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq_status = MagicMock()
        mock_select.eq.return_value = mock_eq_status
        mock_lte = MagicMock()
        mock_eq_status.lte.return_value = mock_lte
        mock_limit = MagicMock()
        mock_lte.limit.return_value = mock_limit
        mock_limit.execute.return_value = MagicMock(
            data=[{"id": claim_id, "created_at": "2026-09-24T00:00:00Z", "action_type": "like"}]
        )

        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq_id = MagicMock()
        mock_update.eq.return_value = mock_eq_id
        mock_eq_cas = MagicMock()
        mock_eq_id.eq.return_value = mock_eq_cas
        mock_eq_cas.execute.return_value = MagicMock(data=[{"id": claim_id}])

        recover_stale_engagement_claims(client=mock_client, stale_minutes=15, force=True)

        # Confirm delete() was NEVER called
        mock_table.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_late_worker_cannot_overwrite_needs_review_in_session_executor(self) -> None:
        """_update_claim_status must fail safely if row is no longer in 'claimed' status."""
        claim_id = str(uuid4())
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq_id = MagicMock()
        mock_update.eq.return_value = mock_eq_id
        mock_eq_status = MagicMock()
        mock_eq_id.eq.return_value = mock_eq_status
        # Returns empty list -> CAS match failed
        mock_eq_status.execute.return_value = MagicMock(data=[])

        executor = SessionExecutor(
            account_id=str(uuid4()),
            unipile_account_id="acc-1",
            company_profile_id=str(uuid4()),
            user_id=str(uuid4()),
            client=mock_client,
        )

        updated = await executor._update_claim_status(
            claim_id=claim_id,
            status=EngagementLogStatus.SUCCEEDED,
            provider_result_id="res-1",
        )

        assert updated is False
        mock_eq_id.eq.assert_called_with("status", EngagementLogStatus.CLAIMED.value)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. UNIFIED ACTIVITY API (F2.3)
# ═══════════════════════════════════════════════════════════════════════════════


class MockSupabaseTable:
    """Mock PostgREST table that accurately mimics filtering, chaining, and counts."""

    def __init__(self, data: list[dict[str, Any]] | None = None, count: int | None = None) -> None:
        self._data = list(data) if data is not None else []
        self._count = count if count is not None else len(self._data)
        self.limit_calls: list[int] = []

    def select(self, *args: Any, **kwargs: Any) -> _MockQuery:
        is_count = kwargs.get("count") == "exact"
        return _MockQuery(self, list(self._data), is_count=is_count)


class _MockQuery:
    def __init__(
        self, table: MockSupabaseTable, current_data: list[dict[str, Any]], is_count: bool = False
    ) -> None:
        self.table = table
        self.data = current_data
        self.is_count = is_count

    def eq(self, col: str, val: Any) -> _MockQuery:
        filtered = [r for r in self.data if col not in r or str(r.get(col)) == str(val)]
        return _MockQuery(self.table, filtered, is_count=self.is_count)

    def in_(self, col: str, vals: Any) -> _MockQuery:
        val_set = {str(v) for v in vals}
        filtered = [r for r in self.data if col not in r or str(r.get(col)) in val_set]
        return _MockQuery(self.table, filtered, is_count=self.is_count)

    @property
    def not_(self) -> _MockNotQuery:
        return _MockNotQuery(self)

    def is_(self, col: str, val: Any) -> _MockQuery:
        if val == "null":
            filtered = [r for r in self.data if col not in r or r.get(col) is None]
        else:
            filtered = [r for r in self.data if col in r and r.get(col) is not None]
        return _MockQuery(self.table, filtered, is_count=self.is_count)

    def gte(self, col: str, val: Any) -> _MockQuery:
        return self

    def lte(self, col: str, val: Any) -> _MockQuery:
        return self

    def order(self, *args: Any, **kwargs: Any) -> _MockQuery:
        return self

    def limit(self, val: int) -> _MockQuery:
        self.table.limit_calls.append(val)
        return _MockQuery(self.table, self.data[:val], is_count=self.is_count)

    def execute(self) -> MagicMock:
        if self.is_count:
            return MagicMock(count=self.table._count, data=[])
        return MagicMock(data=self.data, count=0)


class _MockNotQuery:
    def __init__(self, query: _MockQuery) -> None:
        self.query = query

    def is_(self, col: str, val: Any) -> _MockQuery:
        if val == "null":
            filtered = [r for r in self.query.data if col in r and r.get(col) is not None]
        else:
            filtered = [r for r in self.query.data if col not in r or r.get(col) is None]
        return _MockQuery(self.query.table, filtered, is_count=self.query.is_count)

    def in_(self, col: str, vals: Any) -> _MockQuery:
        val_set = {str(v) for v in vals}
        filtered = [r for r in self.query.data if col in r and str(r.get(col)) not in val_set]
        return _MockQuery(self.query.table, filtered, is_count=self.query.is_count)


class TestUnifiedActivityAPI:
    """Verify GET /api/v1/autopilot/activity/unified multi-tenant history."""

    @pytest.mark.asyncio
    async def test_unified_activity_merges_and_sorts_descending(self) -> None:
        """Publishes and engagements must be merged and sorted newest first."""
        user_id = str(uuid4())
        camp_id = str(uuid4())
        brand_id = str(uuid4())

        user = AuthenticatedUser(id=user_id, email="owner@corp.com", roles=["authenticated"])

        mock_client = MagicMock()

        # 1. Campaigns query
        mock_camp_table = MockSupabaseTable(
            data=[
                {
                    "id": camp_id,
                    "name": "Growth Q3",
                    "company_profile_id": brand_id,
                    "organization_id": user_id,
                }
            ]
        )

        # 2. Posts queries
        post_row_old = {
            "id": str(uuid4()),
            "campaign_id": camp_id,
            "status": "published",
            "published_at": "2026-09-24T08:00:00Z",
            "hook": "Old published post",
            "full_content": "Content 1",
            "created_at": "2026-09-24T07:50:00Z",
        }
        post_row_new = {
            "id": str(uuid4()),
            "campaign_id": camp_id,
            "status": "published",
            "published_at": "2026-09-24T12:00:00Z",
            "hook": "Newest published post",
            "full_content": "Content 2",
            "created_at": "2026-09-24T11:50:00Z",
        }

        mock_post_table = MockSupabaseTable(data=[post_row_new, post_row_old], count=2)

        # 3. Engagement queries
        eng_row_mid = {
            "id": str(uuid4()),
            "user_id": user_id,
            "company_profile_id": brand_id,
            "action_type": "like",
            "status": "succeeded",
            "completed_at": "2026-09-24T10:00:00Z",
            "created_at": "2026-09-24T09:59:00Z",
            "target_post_id": "urn:li:post:123",
        }

        mock_eng_table = MockSupabaseTable(data=[eng_row_mid], count=1)

        def table_dispatch(name: str) -> Any:
            if name == "campaigns":
                return mock_camp_table
            if name == "linkedin_posts":
                return mock_post_table
            if name == "linkedin_engagement_log":
                return mock_eng_table
            return MagicMock()

        mock_client.table.side_effect = table_dispatch

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res = await get_unified_activity(
                company_profile_id=None,
                source_type="all",
                action_type="all",
                user=user,
            )

        assert res["total"] == 3
        events = res["events"]
        assert len(events) == 3

        # Confirm strict descending timestamp order: 12:00 -> 10:00 -> 08:00
        assert events[0]["timestamp"] == "2026-09-24T12:00:00Z"
        assert events[0]["source_type"] == "publishing"
        assert events[0]["action_type"] == "post"
        assert events[0]["target_context"]["campaign_name"] == "Growth Q3"

        assert events[1]["timestamp"] == "2026-09-24T10:00:00Z"
        assert events[1]["source_type"] == "engagement"
        assert events[1]["action_type"] == "like"

        assert events[2]["timestamp"] == "2026-09-24T08:00:00Z"
        assert events[2]["source_type"] == "publishing"

    @pytest.mark.asyncio
    async def test_unified_activity_source_type_filter(self) -> None:
        """Filtering by source_type='publishing' must not query engagement."""
        user = AuthenticatedUser(id=str(uuid4()), email="test@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        # campaigns
        mock_camp_table = MagicMock()
        mock_client.table.side_effect = lambda t: (
            mock_camp_table if t == "campaigns" else MagicMock()
        )
        mock_camp_select = MagicMock()
        mock_camp_table.select.return_value = mock_camp_select
        mock_camp_eq = MagicMock()
        mock_camp_select.eq.return_value = mock_camp_eq
        mock_camp_eq.execute.return_value = MagicMock(data=[])

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res = await get_unified_activity(
                source_type="publishing",
                user=user,
            )

        assert res["total"] == 0
        assert res["events"] == []
        # linkedin_engagement_log should not have been queried
        call_tables = [c[0][0] for c in mock_client.table.call_args_list]
        assert "linkedin_engagement_log" not in call_tables

    @pytest.mark.asyncio
    async def test_unified_activity_action_type_filter(self) -> None:
        """Filtering by action_type='like' must not query publishing."""
        user = AuthenticatedUser(id=str(uuid4()), email="test@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        mock_eng_table = MagicMock()
        mock_client.table.side_effect = lambda t: (
            mock_eng_table if t == "linkedin_engagement_log" else MagicMock()
        )
        mock_eng_select = MagicMock()
        mock_eng_table.select.return_value = mock_eng_select
        mock_eng_eq_user = MagicMock()
        mock_eng_select.eq.return_value = mock_eng_eq_user
        mock_eng_eq_action = MagicMock()
        mock_eng_eq_user.eq.return_value = mock_eng_eq_action
        mock_eng_eq_action.execute.return_value = MagicMock(count=0)
        mock_eng_order = MagicMock()
        mock_eng_eq_action.order.return_value = mock_eng_order
        mock_eng_limit = MagicMock()
        mock_eng_order.limit.return_value = mock_eng_limit
        mock_eng_limit.execute.return_value = MagicMock(data=[])

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res = await get_unified_activity(
                action_type="like",
                user=user,
            )

        assert res["total"] == 0
        call_tables = [c[0][0] for c in mock_client.table.call_args_list]
        assert "campaigns" not in call_tables
        assert "linkedin_posts" not in call_tables

    @pytest.mark.asyncio
    async def test_unified_activity_pagination_and_has_more(self) -> None:
        """Pagination limit/offset and has_more must calculate correctly."""
        user = AuthenticatedUser(id=str(uuid4()), email="user@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        # 3 engagement records
        logs = [
            {
                "id": str(uuid4()),
                "action_type": "like",
                "status": "succeeded",
                "completed_at": f"2026-09-24T0{i}:00:00Z",
            }
            for i in range(1, 4)
        ]

        mock_eng_table = MockSupabaseTable(data=logs, count=3)
        mock_client.table.side_effect = lambda t: (
            mock_eng_table if t == "linkedin_engagement_log" else MagicMock()
        )

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res = await get_unified_activity(
                source_type="engagement",
                limit=2,
                offset=0,
                user=user,
            )

        assert res["total"] == 3
        assert len(res["events"]) == 2
        assert res["limit"] == 2
        assert res["offset"] == 0
        assert res["has_more"] is True

    @pytest.mark.asyncio
    async def test_tenant_isolation_user_a_cannot_see_user_b_publishing(self) -> None:
        """User A querying unified activity only queries campaigns owned by User A."""
        user_a = AuthenticatedUser(id=str(uuid4()), email="usera@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        mock_camp_table = MagicMock()
        mock_client.table.side_effect = lambda t: (
            mock_camp_table if t == "campaigns" else MagicMock()
        )
        mock_camp_select = MagicMock()
        mock_camp_table.select.return_value = mock_camp_select
        mock_camp_eq = MagicMock()
        mock_camp_select.eq.return_value = mock_camp_eq
        mock_camp_eq.execute.return_value = MagicMock(data=[])

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            await get_unified_activity(source_type="publishing", user=user_a)

        # Assert campaigns query explicitly checked organization_id == User A's ID
        mock_camp_select.eq.assert_called_with("organization_id", str(user_a.id))

    @pytest.mark.asyncio
    async def test_tenant_isolation_user_a_cannot_see_user_b_engagement(self) -> None:
        """User A querying unified activity only queries engagement logs owned by User A."""
        user_a = AuthenticatedUser(id=str(uuid4()), email="usera@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        mock_eng_table = MagicMock()
        mock_client.table.side_effect = lambda t: (
            mock_eng_table if t == "linkedin_engagement_log" else MagicMock()
        )
        mock_eng_select = MagicMock()
        mock_eng_table.select.return_value = mock_eng_select
        mock_eng_eq = MagicMock()
        mock_eng_select.eq.return_value = mock_eng_eq
        mock_eng_eq.execute.return_value = MagicMock(count=0)
        mock_eng_order = MagicMock()
        mock_eng_eq.order.return_value = mock_eng_order
        mock_eng_limit = MagicMock()
        mock_eng_order.limit.return_value = mock_eng_limit
        mock_eng_limit.execute.return_value = MagicMock(data=[])

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            await get_unified_activity(source_type="engagement", user=user_a)

        # Assert engagement query strictly filtered by user_id == User A's ID
        mock_eng_select.eq.assert_called_with("user_id", str(user_a.id))

    @pytest.mark.asyncio
    async def test_company_profile_ownership_validation_rejects_unowned_brand(self) -> None:
        """Querying with a company_profile_id not owned by user raises 404."""
        user = AuthenticatedUser(id=str(uuid4()), email="user@corp.com", roles=["authenticated"])
        foreign_brand_id = str(uuid4())

        with (
            patch(
                "src.api.v1.autopilot._resolve_user_brand",
                side_effect=HTTPException(
                    status_code=404, detail="Brand profile not found or access denied."
                ),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_unified_activity(company_profile_id=foreign_brand_id, user=user)

        assert exc_info.value.status_code == 404
        assert "Brand profile not found or access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_sanitizes_error_messages_in_unified_response(self) -> None:
        """Secrets and Bearer tokens inside error_message must be redacted."""
        user = AuthenticatedUser(id=str(uuid4()), email="owner@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        leaked_secret_error = (
            "Failed to call provider: Authorization: Bearer SECRET_TOKEN_12345 with api_key=KEY_ABC"
        )
        raw_log = {
            "id": str(uuid4()),
            "user_id": str(user.id),
            "action_type": "comment",
            "status": "failed",
            "created_at": "2026-09-24T12:00:00Z",
            "error_message": leaked_secret_error,
        }

        mock_eng_table = MockSupabaseTable(data=[raw_log], count=1)
        mock_client.table.side_effect = lambda t: (
            mock_eng_table if t == "linkedin_engagement_log" else MagicMock()
        )

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res = await get_unified_activity(source_type="engagement", user=user)

        sanitized_err = res["events"][0]["error_message"]
        assert sanitized_err is not None
        assert "SECRET_TOKEN_12345" not in sanitized_err
        assert "KEY_ABC" not in sanitized_err
        assert "[REDACTED]" in sanitized_err

    @pytest.mark.asyncio
    async def test_legacy_activity_contract_preserved(self) -> None:
        """GET /activity legacy contract must return {events, total, company_profile_id} unchanged."""
        user = AuthenticatedUser(id=str(uuid4()), email="legacy@corp.com", roles=["authenticated"])
        brand_id = str(uuid4())

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_order = MagicMock()
        mock_eq.order.return_value = mock_order
        mock_limit = MagicMock()
        mock_order.limit.return_value = mock_limit
        mock_limit.execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "action_type": "like"}]
        )

        with (
            patch("src.api.v1.autopilot._resolve_user_brand", return_value={"id": brand_id}),
            patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client),
        ):
            res = await get_engagement_activity(company_profile_id=brand_id, user=user)

        assert "events" in res
        assert "total" in res
        assert "company_profile_id" in res
        assert res["total"] == 1
        assert res["company_profile_id"] == brand_id
        # Legacy does NOT have offset, limit, has_more
        assert "has_more" not in res

    @pytest.mark.asyncio
    async def test_unified_activity_offset_450_limit_100_returns_full_100_items(self) -> None:
        """offset=450, limit=100 returns full 100 items when 600 items exist."""
        user = AuthenticatedUser(id=str(uuid4()), email="user@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        total_count = 600
        # Generate 550 engagement records (fetch_limit = 450 + 100 = 550)
        logs = [
            {
                "id": str(uuid4()),
                "action_type": "like",
                "status": "succeeded",
                "completed_at": (
                    datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC) - timedelta(minutes=i)
                ).isoformat(),
            }
            for i in range(550)
        ]

        mock_eng_table = MockSupabaseTable(data=logs, count=total_count)
        mock_client.table.side_effect = lambda t: (
            mock_eng_table if t == "linkedin_engagement_log" else MagicMock()
        )

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res = await get_unified_activity(
                source_type="engagement",
                limit=100,
                offset=450,
                user=user,
            )

        # Verify query requested 550 items (450 + 100) instead of being capped at 500
        assert 550 in mock_eng_table.limit_calls
        assert res["total"] == 600
        assert len(res["events"]) == 100
        assert res["offset"] == 450
        assert res["limit"] == 100
        assert res["has_more"] is True

    @pytest.mark.asyncio
    async def test_unified_activity_offset_500_limit_50_returns_50_items(self) -> None:
        """offset=500, limit=50 returns 50 items when 600 items exist."""
        user = AuthenticatedUser(id=str(uuid4()), email="user@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        total_count = 600
        # Generate 550 engagement records (fetch_limit = 500 + 50 = 550)
        logs = [
            {
                "id": str(uuid4()),
                "action_type": "like",
                "status": "succeeded",
                "completed_at": (
                    datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC) - timedelta(minutes=i)
                ).isoformat(),
            }
            for i in range(550)
        ]

        mock_eng_table = MockSupabaseTable(data=logs, count=total_count)
        mock_client.table.side_effect = lambda t: (
            mock_eng_table if t == "linkedin_engagement_log" else MagicMock()
        )

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res = await get_unified_activity(
                source_type="engagement",
                limit=50,
                offset=500,
                user=user,
            )

        # Verify query requested 550 items (500 + 50)
        assert 550 in mock_eng_table.limit_calls
        assert res["total"] == 600
        assert len(res["events"]) == 50
        assert res["offset"] == 500
        assert res["limit"] == 50
        assert res["has_more"] is True

    def test_unified_activity_offset_gt_1000_rejected_by_fastapi(self) -> None:
        """offset > 1000 is rejected by FastAPI request validation with 422."""
        from fastapi.testclient import TestClient

        from src.api.dependencies import get_authenticated_user
        from src.main import app

        user = AuthenticatedUser(id=str(uuid4()), email="user@corp.com", roles=["authenticated"])
        app.dependency_overrides[get_authenticated_user] = lambda: user
        try:
            client = TestClient(app)
            response = client.get("/api/v1/autopilot/activity/unified?offset=1001&limit=50")
            assert response.status_code == 422
            data = response.json()
            assert data.get("error") == "validation_error"
            assert any(
                "offset" in str(d.get("field", "")) and "1000" in str(d.get("message", ""))
                for d in data.get("details", [])
            )
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unified_activity_final_partial_page_has_more_false(self) -> None:
        """Final partial page (e.g. 25 items when total=525) must have has_more=false."""
        user = AuthenticatedUser(id=str(uuid4()), email="user@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        total_count = 525
        # Total is 525. For offset=500, limit=50, only 25 items remain.
        logs = [
            {
                "id": str(uuid4()),
                "action_type": "like",
                "status": "succeeded",
                "completed_at": (
                    datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC) - timedelta(minutes=i)
                ).isoformat(),
            }
            for i in range(525)
        ]

        mock_eng_table = MockSupabaseTable(data=logs, count=total_count)
        mock_client.table.side_effect = lambda t: (
            mock_eng_table if t == "linkedin_engagement_log" else MagicMock()
        )

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res = await get_unified_activity(
                source_type="engagement",
                limit=50,
                offset=500,
                user=user,
            )

        assert res["total"] == 525
        assert len(res["events"]) == 25
        # offset (500) + len(events) (25) = 525 == total (525) -> has_more is False
        assert res["has_more"] is False

    @pytest.mark.asyncio
    async def test_unified_activity_empty_page_beyond_total_has_more_false(self) -> None:
        """Empty page beyond total (offset=500, total=500) must have has_more=false."""
        user = AuthenticatedUser(id=str(uuid4()), email="user@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        total_count = 500
        logs = [
            {
                "id": str(uuid4()),
                "action_type": "like",
                "status": "succeeded",
                "completed_at": (
                    datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC) - timedelta(minutes=i)
                ).isoformat(),
            }
            for i in range(500)
        ]

        mock_eng_table = MockSupabaseTable(data=logs, count=total_count)
        mock_client.table.side_effect = lambda t: (
            mock_eng_table if t == "linkedin_engagement_log" else MagicMock()
        )

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res = await get_unified_activity(
                source_type="engagement",
                limit=50,
                offset=500,
                user=user,
            )

        assert res["total"] == 500
        assert len(res["events"]) == 0
        assert res["has_more"] is False

    @pytest.mark.asyncio
    async def test_unified_activity_total_remains_exact_under_filters(self) -> None:
        """Exact count queries apply all active filters (source, action, status, dates)."""
        user = AuthenticatedUser(id=str(uuid4()), email="user@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        mock_eng_table = MagicMock()
        mock_client.table.side_effect = lambda t: (
            mock_eng_table if t == "linkedin_engagement_log" else MagicMock()
        )

        mock_select = MagicMock()
        mock_eng_table.select.return_value = mock_select
        mock_eq_user = MagicMock()
        mock_select.eq.return_value = mock_eq_user
        mock_eq_action = MagicMock()
        mock_eq_user.eq.return_value = mock_eq_action
        mock_eq_status = MagicMock()
        mock_eq_action.eq.return_value = mock_eq_status
        mock_gte_date = MagicMock()
        mock_eq_status.gte.return_value = mock_gte_date
        mock_lte_date = MagicMock()
        mock_gte_date.lte.return_value = mock_lte_date

        # Exact count result
        mock_lte_date.execute.return_value = MagicMock(count=42)

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res = await get_unified_activity(
                source_type="engagement",
                action_type="comment",
                filter_status="succeeded",
                start_date="2026-09-01T00:00:00Z",
                end_date="2026-09-24T23:59:59Z",
                limit=20,
                offset=0,
                user=user,
            )

        assert res["total"] == 42
        mock_select.eq.assert_called_with("user_id", str(user.id))
        mock_eq_user.eq.assert_called_with("action_type", "comment")
        mock_eq_action.eq.assert_called_with("status", "succeeded")
        mock_eq_status.gte.assert_called_with("created_at", "2026-09-01T00:00:00Z")
        mock_gte_date.lte.assert_called_with("created_at", "2026-09-24T23:59:59Z")

    @pytest.mark.asyncio
    async def test_older_created_post_with_future_scheduled_at_does_not_cause_duplicate_pages(
        self,
    ) -> None:
        """Older created_at post with future scheduled_at must NOT cause page duplicates."""
        user_id = str(uuid4())
        camp_id = str(uuid4())
        user = AuthenticatedUser(id=user_id, email="owner@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        mock_camp_table = MockSupabaseTable(
            data=[
                {
                    "id": camp_id,
                    "name": "Growth Q3",
                    "company_profile_id": None,
                    "organization_id": user_id,
                }
            ]
        )

        # 5 posts created recently with older scheduled/published dates
        base_time = datetime(2026, 9, 22, 15, 0, 0, tzinfo=UTC)
        recent_posts = [
            {
                "id": f"recent-{i}",
                "campaign_id": camp_id,
                "status": "published",
                "published_at": (base_time - timedelta(hours=i)).isoformat(),
                "created_at": (base_time + timedelta(minutes=i)).isoformat(),
            }
            for i in range(1, 6)
        ]

        # 1 post created way earlier (lower created_at rank) but scheduled for future (higher canonical rank!)
        future_post = {
            "id": "future-scheduled",
            "campaign_id": camp_id,
            "status": "scheduled",
            "scheduled_at": "2026-10-20T09:00:00Z",
            "created_at": "2026-09-01T00:00:00Z",
        }

        all_posts = [future_post] + recent_posts
        mock_post_table = MockSupabaseTable(data=all_posts, count=len(all_posts))
        mock_eng_table = MockSupabaseTable(data=[], count=0)

        def table_dispatch(name: str) -> Any:
            if name == "campaigns":
                return mock_camp_table
            if name == "linkedin_posts":
                return mock_post_table
            if name == "linkedin_engagement_log":
                return mock_eng_table
            return MagicMock()

        mock_client.table.side_effect = table_dispatch

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            # Page 1: limit=5, offset=0
            p1_res = await get_unified_activity(
                source_type="publishing",
                limit=5,
                offset=0,
                user=user,
            )
            # Page 2: limit=5, offset=5
            p2_res = await get_unified_activity(
                source_type="publishing",
                limit=5,
                offset=5,
                user=user,
            )

        p1_ids = [e["id"] for e in p1_res["events"]]
        p2_ids = [e["id"] for e in p2_res["events"]]

        # future-scheduled MUST be on page 1 because canonical timestamp is in October!
        assert "future-scheduled" in p1_ids
        assert p1_ids[0] == "future-scheduled"

        # Disjoint: zero duplicates across page 1 and page 2
        assert set(p1_ids).intersection(set(p2_ids)) == set()
        assert len(p1_ids) == 5
        assert len(p2_ids) == 1

    @pytest.mark.asyncio
    async def test_mixed_publishing_and_engagement_pagination_disjoint_pages(self) -> None:
        """Mixed publishing + engagement pagination yields disjoint pages."""
        user_id = str(uuid4())
        camp_id = str(uuid4())
        user = AuthenticatedUser(id=user_id, email="owner@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        mock_camp_table = MockSupabaseTable(
            data=[
                {
                    "id": camp_id,
                    "name": "Growth Q3",
                    "company_profile_id": None,
                    "organization_id": user_id,
                }
            ]
        )

        posts = [
            {
                "id": f"post-{i}",
                "campaign_id": camp_id,
                "status": "published",
                "published_at": f"2026-09-24T{15+i}:00:00Z",
                "created_at": f"2026-09-24T{15+i}:00:00Z",
            }
            for i in range(5)
        ]

        logs = [
            {
                "id": f"eng-{i}",
                "user_id": user_id,
                "action_type": "like",
                "status": "succeeded",
                "completed_at": f"2026-09-24T{10+i}:00:00Z",
                "created_at": f"2026-09-24T{10+i}:00:00Z",
            }
            for i in range(5)
        ]

        mock_post_table = MockSupabaseTable(data=posts, count=5)
        mock_eng_table = MockSupabaseTable(data=logs, count=5)

        def table_dispatch(name: str) -> Any:
            if name == "campaigns":
                return mock_camp_table
            if name == "linkedin_posts":
                return mock_post_table
            if name == "linkedin_engagement_log":
                return mock_eng_table
            return MagicMock()

        mock_client.table.side_effect = table_dispatch

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            p1_res = await get_unified_activity(limit=5, offset=0, user=user)
            p2_res = await get_unified_activity(limit=5, offset=5, user=user)

        p1_ids = [e["id"] for e in p1_res["events"]]
        p2_ids = [e["id"] for e in p2_res["events"]]

        assert len(p1_ids) == 5
        assert len(p2_ids) == 5
        assert set(p1_ids).intersection(set(p2_ids)) == set()

    @pytest.mark.asyncio
    async def test_equal_canonical_timestamps_deterministic_ordering_by_source_and_id(self) -> None:
        """Equal canonical timestamps sort deterministically by source_type then id DESC."""
        user_id = str(uuid4())
        camp_id = str(uuid4())
        user = AuthenticatedUser(id=user_id, email="owner@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        mock_camp_table = MockSupabaseTable(
            data=[
                {
                    "id": camp_id,
                    "name": "Growth Q3",
                    "company_profile_id": None,
                    "organization_id": user_id,
                }
            ]
        )

        same_ts = "2026-09-24T12:00:00Z"
        posts = [
            {"id": "uuid-post-b", "campaign_id": camp_id, "status": "draft", "created_at": same_ts},
            {"id": "uuid-post-a", "campaign_id": camp_id, "status": "draft", "created_at": same_ts},
        ]
        logs = [
            {
                "id": "uuid-eng-z",
                "user_id": user_id,
                "action_type": "like",
                "status": "succeeded",
                "completed_at": same_ts,
            },
        ]

        mock_post_table = MockSupabaseTable(data=posts, count=2)
        mock_eng_table = MockSupabaseTable(data=logs, count=1)

        def table_dispatch(name: str) -> Any:
            if name == "campaigns":
                return mock_camp_table
            if name == "linkedin_posts":
                return mock_post_table
            if name == "linkedin_engagement_log":
                return mock_eng_table
            return MagicMock()

        mock_client.table.side_effect = table_dispatch

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res = await get_unified_activity(limit=10, offset=0, user=user)

        events = res["events"]
        assert len(events) == 3
        # source_type "publishing" before "engagement" ('p' > 'e' in reverse sort)
        assert events[0]["source_type"] == "publishing"
        assert events[0]["id"] == "uuid-post-b"
        assert events[1]["source_type"] == "publishing"
        assert events[1]["id"] == "uuid-post-a"
        assert events[2]["source_type"] == "engagement"
        assert events[2]["id"] == "uuid-eng-z"

    @pytest.mark.asyncio
    async def test_different_candidate_window_sizes_yield_identical_first_n_events(self) -> None:
        """First 10 ordered events remain identical whether candidate window is 10, 20, or larger."""
        user_id = str(uuid4())
        camp_id = str(uuid4())
        user = AuthenticatedUser(id=user_id, email="owner@corp.com", roles=["authenticated"])
        mock_client = MagicMock()

        mock_camp_table = MockSupabaseTable(
            data=[
                {
                    "id": camp_id,
                    "name": "Growth Q3",
                    "company_profile_id": None,
                    "organization_id": user_id,
                }
            ]
        )

        posts = [
            {
                "id": f"p-{i:02d}",
                "campaign_id": camp_id,
                "status": "published",
                "published_at": (
                    datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC) - timedelta(hours=i)
                ).isoformat(),
                "created_at": (
                    datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC) - timedelta(hours=i)
                ).isoformat(),
            }
            for i in range(15)
        ]
        logs = [
            {
                "id": f"e-{i:02d}",
                "user_id": user_id,
                "action_type": "like",
                "status": "succeeded",
                "completed_at": (
                    datetime(2026, 9, 24, 11, 30, 0, tzinfo=UTC) - timedelta(hours=i)
                ).isoformat(),
                "created_at": (
                    datetime(2026, 9, 24, 11, 30, 0, tzinfo=UTC) - timedelta(hours=i)
                ).isoformat(),
            }
            for i in range(15)
        ]

        mock_post_table = MockSupabaseTable(data=posts, count=15)
        mock_eng_table = MockSupabaseTable(data=logs, count=15)

        def table_dispatch(name: str) -> Any:
            if name == "campaigns":
                return mock_camp_table
            if name == "linkedin_posts":
                return mock_post_table
            if name == "linkedin_engagement_log":
                return mock_eng_table
            return MagicMock()

        mock_client.table.side_effect = table_dispatch

        with patch("src.api.v1.autopilot.get_supabase_client", return_value=mock_client):
            res_window_10 = await get_unified_activity(limit=10, offset=0, user=user)
            res_window_20 = await get_unified_activity(limit=20, offset=0, user=user)

        events_10 = res_window_10["events"]
        events_20_first_10 = res_window_20["events"][:10]

        assert [e["id"] for e in events_10] == [e["id"] for e in events_20_first_10]
