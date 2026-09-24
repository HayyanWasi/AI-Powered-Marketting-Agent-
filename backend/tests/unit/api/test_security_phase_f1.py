"""Unit tests for Phase F1 Security and History Hardening.

Covers:
- Tenant isolation on /operations/history (User A cannot read User B)
- Tenant isolation on /publisher-status (User A cannot see User B posts)
- Ownership verification on DELETE /queue/{job_id} (User A cannot delete User B post)
- Same-user access succeeds
- ExecutionHistoryRepository requires user_id and rejects unowned records
- Error message credential and secret sanitization
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.dependencies import AuthenticatedUser
from src.api.v1.autopilot import delete_queue_job, get_publisher_status
from src.api.v1.operations import get_execution_history
from src.modules.operations.constants import ExecutionStatus
from src.modules.operations.errors import HistoryQueryError
from src.modules.operations.models.execution_history import ExecutionHistoryRecord
from src.modules.operations.repositories.execution_history_repository import (
    ExecutionHistoryRepository,
)
from src.modules.operations.services.platform_operations import PlatformOperationsService
from src.utils.sanitizer import sanitize_error_message

# ═══════════════════════════════════════════════════════════════════════════════
# 1. /operations/history Tenant Isolation & Schema Hardening
# ═══════════════════════════════════════════════════════════════════════════════


class TestExecutionHistoryTenantSecurity:
    """Verify execution_history isolation between users."""

    @pytest.mark.asyncio
    async def test_repository_query_filters_by_user_id(self) -> None:
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_order = MagicMock()
        mock_eq.order.return_value = mock_order
        mock_range = MagicMock()
        mock_order.range.return_value = mock_range
        mock_range.execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "workflow_id": "wf-1"}]
        )

        repo = ExecutionHistoryRepository(supabase=mock_client)
        user_a_id = uuid4()

        results = await repo.query(user_id=user_a_id)

        # Assert .eq("user_id", str(user_a_id)) was strictly invoked
        mock_select.eq.assert_called_with("user_id", str(user_a_id))
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_user_a_cannot_read_user_b_execution_history(self) -> None:
        user_a_id = uuid4()
        user_b_id = uuid4()

        mock_ops = MagicMock(spec=PlatformOperationsService)
        mock_ops.get_execution_history = AsyncMock(return_value=[])

        user_a = AuthenticatedUser(id=str(user_a_id), email="usera@corp.com", roles=["authenticated"])

        # User A calls endpoint
        await get_execution_history(user=user_a, operations=mock_ops)

        # Verify operations service was called with User A's ID, NEVER user B's
        mock_ops.get_execution_history.assert_called_once_with(
            user_id=str(user_a_id),
            workflow_id=None,
            status=None,
            limit=100,
            offset=0,
        )
        assert mock_ops.get_execution_history.call_args.kwargs["user_id"] != str(user_b_id)

    @pytest.mark.asyncio
    async def test_execution_history_insert_rejects_missing_user_id(self) -> None:
        mock_client = MagicMock()
        repo = ExecutionHistoryRepository(supabase=mock_client)

        unowned_record = ExecutionHistoryRecord(
            workflow_id="wf-test",
            status=ExecutionStatus.COMPLETED,
            user_id=None,  # Missing owner
        )

        with pytest.raises(HistoryQueryError) as exc_info:
            await repo.insert(unowned_record)

        assert "requires a valid user_id owner" in str(exc_info.value)
        mock_client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_execution_history_insert_persists_user_id(self) -> None:
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = MagicMock(data=[])

        repo = ExecutionHistoryRepository(supabase=mock_client)
        user_id = uuid4()
        record = ExecutionHistoryRecord(
            workflow_id="wf-owned",
            status=ExecutionStatus.COMPLETED,
            user_id=user_id,
        )

        await repo.insert(record)

        mock_client.table.assert_called_once_with("execution_history")
        inserted_payload = mock_table.insert.call_args[0][0]
        assert inserted_payload["user_id"] == str(user_id)
        assert inserted_payload["workflow_id"] == "wf-owned"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. /publisher-status Tenant Isolation
# ═══════════════════════════════════════════════════════════════════════════════


class TestPublisherStatusTenantSecurity:
    """Verify /publisher-status never exposes other users' posts."""

    @pytest.mark.asyncio
    async def test_user_without_campaigns_sees_zero_posts(self) -> None:
        user_a = AuthenticatedUser(id=str(uuid4()), email="usera@corp.com", roles=["authenticated"])

        mock_campaigns_repo = MagicMock()
        mock_camp_table = MagicMock()
        mock_campaigns_repo.client.table.return_value = mock_camp_table
        mock_camp_select = MagicMock()
        mock_camp_table.select.return_value = mock_camp_select
        mock_camp_eq = MagicMock()
        mock_camp_select.eq.return_value = mock_camp_eq
        mock_camp_eq.execute.return_value = MagicMock(data=[])  # User A has 0 campaigns

        mock_posts_repo = MagicMock()

        with patch("src.api.v1.autopilot.BaseRepository") as mock_base_repo:
            mock_base_repo.side_effect = lambda name: (
                mock_campaigns_repo if name == "campaigns" else mock_posts_repo
            )

            status_result = await get_publisher_status(user=user_a)

            assert status_result["total_posts"] == 0
            assert status_result["by_status"] == {}
            assert status_result["overdue_count"] == 0
            assert status_result["overdue_posts"] == []
            # Crucial: posts table was never queried globally
            mock_posts_repo.client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_a_only_sees_posts_from_own_campaigns(self) -> None:
        user_a = AuthenticatedUser(id=str(uuid4()), email="usera@corp.com", roles=["authenticated"])
        user_a_camp_id = str(uuid4())

        mock_campaigns_repo = MagicMock()
        mock_camp_table = MagicMock()
        mock_campaigns_repo.client.table.return_value = mock_camp_table
        mock_camp_select = MagicMock()
        mock_camp_table.select.return_value = mock_camp_select
        mock_camp_eq = MagicMock()
        mock_camp_select.eq.return_value = mock_camp_eq
        mock_camp_eq.execute.return_value = MagicMock(data=[{"id": user_a_camp_id}])

        mock_posts_repo = MagicMock()
        mock_post_table = MagicMock()
        mock_posts_repo.client.table.return_value = mock_post_table
        mock_post_select = MagicMock()
        mock_post_table.select.return_value = mock_post_select
        mock_post_in = MagicMock()
        mock_post_select.in_.return_value = mock_post_in
        mock_post_in.execute.return_value = MagicMock(
            data=[
                {"id": str(uuid4()), "status": "published", "scheduled_at": None},
                {"id": str(uuid4()), "status": "scheduled", "scheduled_at": "2026-09-20T10:00:00Z"},
            ]
        )

        with patch("src.api.v1.autopilot.BaseRepository") as mock_base_repo:
            mock_base_repo.side_effect = lambda name: (
                mock_campaigns_repo if name == "campaigns" else mock_posts_repo
            )

            status_result = await get_publisher_status(user=user_a)

            mock_camp_select.eq.assert_called_with("organization_id", str(user_a.id))
            mock_post_select.in_.assert_called_with("campaign_id", [user_a_camp_id])
            assert status_result["total_posts"] == 2
            assert status_result["by_status"]["published"] == 1
            assert status_result["by_status"]["scheduled"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DELETE /queue/{job_id} Ownership Enforcement
# ═══════════════════════════════════════════════════════════════════════════════


class TestQueueDeletionTenantSecurity:
    """Verify DELETE /queue/{job_id} strictly checks post -> campaign -> owner."""

    @pytest.mark.asyncio
    async def test_user_a_cannot_delete_user_b_queued_post(self) -> None:
        user_a = AuthenticatedUser(id=str(uuid4()), email="usera@corp.com", roles=["authenticated"])
        user_b_id = uuid4()
        job_id = str(uuid4())
        campaign_b_id = str(uuid4())

        mock_posts_repo = MagicMock()
        mock_post_table = MagicMock()
        mock_posts_repo.client.table.return_value = mock_post_table
        mock_post_select = MagicMock()
        mock_post_table.select.return_value = mock_post_select
        mock_post_eq = MagicMock()
        mock_post_select.eq.return_value = mock_post_eq
        # Post exists and belongs to campaign_b
        mock_post_eq.execute.return_value = MagicMock(
            data=[{"id": job_id, "campaign_id": campaign_b_id}]
        )

        mock_campaigns_repo = MagicMock()
        mock_camp_table = MagicMock()
        mock_campaigns_repo.client.table.return_value = mock_camp_table
        mock_camp_select = MagicMock()
        mock_camp_table.select.return_value = mock_camp_select
        mock_camp_eq = MagicMock()
        mock_camp_select.eq.return_value = mock_camp_eq
        # Campaign B belongs to user B!
        mock_camp_eq.execute.return_value = MagicMock(
            data=[{"id": campaign_b_id, "organization_id": str(user_b_id)}]
        )

        with patch("src.api.v1.autopilot.BaseRepository") as mock_base_repo:
            mock_base_repo.side_effect = lambda name: (
                mock_posts_repo if name == "linkedin_posts" else mock_campaigns_repo
            )

            # Must raise 404 (not 403) to prevent existence leakage
            with pytest.raises(HTTPException) as exc_info:
                await delete_queue_job(job_id=job_id, user=user_a)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Queue item not found"
            # Delete was NOT called
            mock_post_table.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_nonexistent_job_id_returns_404(self) -> None:
        user_a = AuthenticatedUser(id=str(uuid4()), email="usera@corp.com", roles=["authenticated"])
        missing_job_id = str(uuid4())

        mock_posts_repo = MagicMock()
        mock_post_table = MagicMock()
        mock_posts_repo.client.table.return_value = mock_post_table
        mock_post_select = MagicMock()
        mock_post_table.select.return_value = mock_post_select
        mock_post_eq = MagicMock()
        mock_post_select.eq.return_value = mock_post_eq
        mock_post_eq.execute.return_value = MagicMock(data=[])  # Not found

        with patch("src.api.v1.autopilot.BaseRepository", return_value=mock_posts_repo):
            with pytest.raises(HTTPException) as exc_info:
                await delete_queue_job(job_id=missing_job_id, user=user_a)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Queue item not found"
            mock_post_table.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_same_user_can_delete_own_queued_post(self) -> None:
        user_a_id = uuid4()
        user_a = AuthenticatedUser(id=str(user_a_id), email="usera@corp.com", roles=["authenticated"])
        job_id = str(uuid4())
        campaign_a_id = str(uuid4())

        mock_posts_repo = MagicMock()
        mock_post_table = MagicMock()
        mock_posts_repo.client.table.return_value = mock_post_table
        mock_post_select = MagicMock()
        mock_post_table.select.return_value = mock_post_select
        mock_post_eq = MagicMock()
        mock_post_select.eq.return_value = mock_post_eq
        mock_post_eq.execute.return_value = MagicMock(
            data=[{"id": job_id, "campaign_id": campaign_a_id}]
        )

        mock_campaigns_repo = MagicMock()
        mock_camp_table = MagicMock()
        mock_campaigns_repo.client.table.return_value = mock_camp_table
        mock_camp_select = MagicMock()
        mock_camp_table.select.return_value = mock_camp_select
        mock_camp_eq = MagicMock()
        mock_camp_select.eq.return_value = mock_camp_eq
        # Campaign owned by user A
        mock_camp_eq.execute.return_value = MagicMock(
            data=[{"id": campaign_a_id, "organization_id": str(user_a_id)}]
        )

        mock_delete = MagicMock()
        mock_post_table.delete.return_value = mock_delete
        mock_del_eq = MagicMock()
        mock_delete.eq.return_value = mock_del_eq
        mock_del_eq.execute.return_value = MagicMock(data=[{"id": job_id}])

        with patch("src.api.v1.autopilot.BaseRepository") as mock_base_repo:
            mock_base_repo.side_effect = lambda name: (
                mock_posts_repo if name == "linkedin_posts" else mock_campaigns_repo
            )

            res = await delete_queue_job(job_id=job_id, user=user_a)

            assert res["success"] is True
            assert res["id"] == job_id
            assert res["deleted_from_db"] is True
            mock_post_table.delete.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Error Sanitization & Secret Redaction
# ═══════════════════════════════════════════════════════════════════════════════


class TestSecretErrorSanitization:
    """Verify sensitive provider tokens and secrets are redacted."""

    def test_sanitize_bearer_token(self) -> None:
        raw = "HTTP 401: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.secret_signature_here"
        cleaned = sanitize_error_message(raw)
        assert cleaned is not None
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in cleaned
        assert "Bearer [REDACTED]" in cleaned

    def test_sanitize_authorization_header(self) -> None:
        raw = "Error sending request: Authorization: Bearer live_token_abcdef1234567890 in header"
        cleaned = sanitize_error_message(raw)
        assert cleaned is not None
        assert "live_token_abcdef1234567890" not in cleaned
        assert "[REDACTED]" in cleaned

    def test_sanitize_api_keys_and_passwords(self) -> None:
        raw = "Failed call to https://api.provider.com?api_key=sk_live_secret12345&password=SuperSecretPassword99"
        cleaned = sanitize_error_message(raw)
        assert cleaned is not None
        assert "sk_live_secret12345" not in cleaned
        assert "SuperSecretPassword99" not in cleaned
        assert "api_key=[REDACTED]" in cleaned
        assert "password=[REDACTED]" in cleaned

    def test_sanitize_url_credentials(self) -> None:
        raw = "Postgres connection error: postgresql://postgres:MyDbPassword123@db.supabase.co:5432/postgres"
        cleaned = sanitize_error_message(raw)
        assert cleaned is not None
        assert "MyDbPassword123" not in cleaned
        assert "postgresql://[REDACTED]:[REDACTED]@db.supabase.co:5432/postgres" in cleaned

    def test_sanitize_handles_none_and_safe_strings(self) -> None:
        assert sanitize_error_message(None) is None
        safe = "HTTP 404: Prospect profile not found on LinkedIn"
        assert sanitize_error_message(safe) == safe
