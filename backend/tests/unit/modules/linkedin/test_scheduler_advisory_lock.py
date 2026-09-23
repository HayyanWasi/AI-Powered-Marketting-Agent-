"""Unit Tests for Scheduler PostgreSQL Advisory Locking (Fail-Closed Guarantees).

Verifies that the engagement scheduler strictly fails closed:
A. Lock acquired -> SessionExecutor called exactly once, unlocked on completion.
B. Lock contention (pg_try_advisory_lock returns False) -> SessionExecutor called 0 times.
C. DB connection / lock query error -> SessionExecutor called 0 times, NO in-memory fallback.
D. Two scheduler workers for same brand -> Only one enters execution.
E. Acquired lock + executor exception -> Unlock called in finally.
F. Unset DATABASE_URL in production default -> Fails closed, zero engagement actions.
G. In-memory lock allowed only with explicit allow_in_memory=True flag (isolated unit tests).
Zero external LinkedIn / Unipile calls are triggered.
"""

from __future__ import annotations

import asyncio
from datetime import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.config.settings import settings
from src.modules.linkedin.distributed_lock import _PROCESS_LOCKS, BrandAdvisoryLock
from src.modules.linkedin.models import SessionWindow
from src.modules.linkedin.worker.scheduler import _run_brand_session


@pytest.fixture
def sample_session_data() -> dict[str, Any]:
    return {
        "brand_id": str(uuid4()),
        "user_id": str(uuid4()),
        "account": {
            "id": str(uuid4()),
            "unipile_account_id": "test_unipile_acc_123",
        },
        "settings_row": {
            "timezone": "UTC",
            "connection_note_template": "Hi {first_name}",
        },
        "session": SessionWindow(
            start=time(9, 0),
            end=time(9, 30),
            max_actions=5,
            action_types=("like", "comment"),
        ),
        "invite_limit": 10,
        "like_limit": 15,
        "comment_limit": 5,
        "action_types": ("like", "comment"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TEST A: LOCK ACQUIRED -> SESSION EXECUTOR CALLED EXACTLY ONCE
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_a_lock_acquired_executor_called_exactly_once(sample_session_data):
    """When pg_try_advisory_lock succeeds, the engagement session executes once and unlocks."""
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=True)  # Lock acquired
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.close = AsyncMock(return_value=None)

    mock_asyncpg = MagicMock()
    mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

    with (
        patch.object(settings, "DATABASE_URL", "postgresql://mock:5432/db"),
        patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
        patch("src.modules.linkedin.worker.scheduler.SessionExecutor") as mock_executor_cls,
    ):
        mock_instance = AsyncMock()
        mock_executor_cls.return_value = mock_instance

        await _run_brand_session(
            brand_id=sample_session_data["brand_id"],
            user_id=sample_session_data["user_id"],
            account=sample_session_data["account"],
            settings_row=sample_session_data["settings_row"],
            session=sample_session_data["session"],
            invite_limit=sample_session_data["invite_limit"],
            like_limit=sample_session_data["like_limit"],
            comment_limit=sample_session_data["comment_limit"],
            action_types=sample_session_data["action_types"],
        )

        # Executor called exactly once
        mock_instance.execute_session.assert_awaited_once()

        # Unlock and close connection in finally
        mock_conn.execute.assert_awaited_once()
        unlock_call_arg = mock_conn.execute.call_args[0][0]
        assert "pg_advisory_unlock" in unlock_call_arg
        mock_conn.close.assert_awaited_once()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST B: LOCK CONTENTION -> SESSION EXECUTOR CALLED 0 TIMES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_b_lock_contention_skips_session_zero_calls(sample_session_data):
    """When pg_try_advisory_lock returns False (held by another worker), session is skipped."""
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=False)  # Contention
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.close = AsyncMock(return_value=None)

    mock_asyncpg = MagicMock()
    mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

    with (
        patch.object(settings, "DATABASE_URL", "postgresql://mock:5432/db"),
        patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
        patch("src.modules.linkedin.worker.scheduler.SessionExecutor") as mock_executor_cls,
    ):
        mock_instance = AsyncMock()
        mock_executor_cls.return_value = mock_instance

        await _run_brand_session(
            brand_id=sample_session_data["brand_id"],
            user_id=sample_session_data["user_id"],
            account=sample_session_data["account"],
            settings_row=sample_session_data["settings_row"],
            session=sample_session_data["session"],
            invite_limit=sample_session_data["invite_limit"],
            like_limit=sample_session_data["like_limit"],
            comment_limit=sample_session_data["comment_limit"],
            action_types=sample_session_data["action_types"],
        )

        # SessionExecutor must NEVER be called
        mock_instance.execute_session.assert_not_called()
        mock_executor_cls.assert_not_called()

        # Connection closed cleanly
        mock_conn.close.assert_awaited_once()
        # Unlock is NOT called because lock was never held
        mock_conn.execute.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST C: DB LOCK ERROR -> FAILS CLOSED, NO IN-MEMORY FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_c_db_lock_connection_error_fails_closed_no_fallback(sample_session_data):
    """When DB connection raises an exception, session fails closed with zero actions and no fallback."""
    brand_id = sample_session_data["brand_id"]
    _PROCESS_LOCKS.pop(brand_id, None)

    mock_asyncpg = MagicMock()
    mock_asyncpg.connect = AsyncMock(side_effect=OSError("Database connection refused"))

    with (
        patch.object(settings, "DATABASE_URL", "postgresql://mock:5432/db"),
        patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
        patch("src.modules.linkedin.worker.scheduler.SessionExecutor") as mock_executor_cls,
    ):
        mock_instance = AsyncMock()
        mock_executor_cls.return_value = mock_instance

        await _run_brand_session(
            brand_id=brand_id,
            user_id=sample_session_data["user_id"],
            account=sample_session_data["account"],
            settings_row=sample_session_data["settings_row"],
            session=sample_session_data["session"],
            invite_limit=sample_session_data["invite_limit"],
            like_limit=sample_session_data["like_limit"],
            comment_limit=sample_session_data["comment_limit"],
            action_types=sample_session_data["action_types"],
        )

        # Session executor must NOT be called
        mock_instance.execute_session.assert_not_called()
        mock_executor_cls.assert_not_called()

        # Verify NO in-memory fallback lock was created
        assert brand_id not in _PROCESS_LOCKS


@pytest.mark.asyncio
async def test_c_db_lock_query_error_fails_closed_no_fallback(sample_session_data):
    """When fetchval raises a database error, session fails closed, cleans up conn, no fallback."""
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(side_effect=RuntimeError("pg_try_advisory_lock query failed"))
    mock_conn.close = AsyncMock(return_value=None)
    brand_id = sample_session_data["brand_id"]
    _PROCESS_LOCKS.pop(brand_id, None)

    mock_asyncpg = MagicMock()
    mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

    with (
        patch.object(settings, "DATABASE_URL", "postgresql://mock:5432/db"),
        patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
        patch("src.modules.linkedin.worker.scheduler.SessionExecutor") as mock_executor_cls,
    ):
        mock_instance = AsyncMock()
        mock_executor_cls.return_value = mock_instance

        await _run_brand_session(
            brand_id=brand_id,
            user_id=sample_session_data["user_id"],
            account=sample_session_data["account"],
            settings_row=sample_session_data["settings_row"],
            session=sample_session_data["session"],
            invite_limit=sample_session_data["invite_limit"],
            like_limit=sample_session_data["like_limit"],
            comment_limit=sample_session_data["comment_limit"],
            action_types=sample_session_data["action_types"],
        )

        mock_instance.execute_session.assert_not_called()
        mock_conn.close.assert_awaited_once()
        assert brand_id not in _PROCESS_LOCKS


# ═══════════════════════════════════════════════════════════════════════════════
# TEST D: TWO SCHEDULER WORKERS SAME BRAND -> ONLY ONE ENTERS EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_d_two_scheduler_workers_same_brand_mutual_exclusion(sample_session_data):
    """Simulate two concurrent workers for the same brand; exactly one executes."""
    # Shared state simulating PostgreSQL advisory lock
    brand_locks_held: set[int] = set()
    lock_mutex = asyncio.Lock()

    async def mock_connect(dsn: str, timeout: float = 10.0) -> Any:
        conn = AsyncMock()
        held_by_this_conn = False

        async def mock_fetchval(query: str, key: int) -> bool:
            nonlocal held_by_this_conn
            async with lock_mutex:
                if key in brand_locks_held:
                    return False
                brand_locks_held.add(key)
                held_by_this_conn = True
                return True

        async def mock_execute(query: str, key: int) -> None:
            nonlocal held_by_this_conn
            async with lock_mutex:
                if "pg_advisory_unlock" in query and held_by_this_conn:
                    brand_locks_held.discard(key)
                    held_by_this_conn = False

        async def mock_close() -> None:
            nonlocal held_by_this_conn
            async with lock_mutex:
                if held_by_this_conn:
                    held_by_this_conn = False

        conn.fetchval = AsyncMock(side_effect=mock_fetchval)
        conn.execute = AsyncMock(side_effect=mock_execute)
        conn.close = AsyncMock(side_effect=mock_close)
        return conn

    execution_counter = 0

    async def slow_execute_session(*args: Any, **kwargs: Any) -> None:
        nonlocal execution_counter
        execution_counter += 1
        await asyncio.sleep(0.05)  # hold lock while executing

    mock_asyncpg = MagicMock()
    mock_asyncpg.connect = AsyncMock(side_effect=mock_connect)

    with (
        patch.object(settings, "DATABASE_URL", "postgresql://mock:5432/db"),
        patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
        patch("src.modules.linkedin.worker.scheduler.SessionExecutor") as mock_executor_cls,
    ):
        mock_instance = AsyncMock()
        mock_instance.execute_session = AsyncMock(side_effect=slow_execute_session)
        mock_executor_cls.return_value = mock_instance

        # Launch two concurrent workers for the SAME brand simultaneously
        task1 = asyncio.create_task(
            _run_brand_session(
                brand_id=sample_session_data["brand_id"],
                user_id=sample_session_data["user_id"],
                account=sample_session_data["account"],
                settings_row=sample_session_data["settings_row"],
                session=sample_session_data["session"],
                invite_limit=sample_session_data["invite_limit"],
                like_limit=sample_session_data["like_limit"],
                comment_limit=sample_session_data["comment_limit"],
                action_types=sample_session_data["action_types"],
            )
        )
        task2 = asyncio.create_task(
            _run_brand_session(
                brand_id=sample_session_data["brand_id"],
                user_id=sample_session_data["user_id"],
                account=sample_session_data["account"],
                settings_row=sample_session_data["settings_row"],
                session=sample_session_data["session"],
                invite_limit=sample_session_data["invite_limit"],
                like_limit=sample_session_data["like_limit"],
                comment_limit=sample_session_data["comment_limit"],
                action_types=sample_session_data["action_types"],
            )
        )

        await asyncio.gather(task1, task2)

        # Only one worker was allowed to execute
        assert execution_counter == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST E: ACQUIRED LOCK + EXECUTOR EXCEPTION -> UNLOCK CALLED IN FINALLY
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_e_acquired_lock_executor_exception_unlock_called_in_finally(sample_session_data):
    """When executor crashes during execution, lock is guaranteed to be released in finally."""
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=True)  # Lock acquired
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.close = AsyncMock(return_value=None)

    mock_asyncpg = MagicMock()
    mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

    with (
        patch.object(settings, "DATABASE_URL", "postgresql://mock:5432/db"),
        patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
        patch("src.modules.linkedin.worker.scheduler.SessionExecutor") as mock_executor_cls,
    ):
        mock_instance = AsyncMock()
        mock_instance.execute_session = AsyncMock(
            side_effect=RuntimeError("Simulated LLM/Unipile network crash")
        )
        mock_executor_cls.return_value = mock_instance

        # Function handles exception gracefully without leaking lock
        await _run_brand_session(
            brand_id=sample_session_data["brand_id"],
            user_id=sample_session_data["user_id"],
            account=sample_session_data["account"],
            settings_row=sample_session_data["settings_row"],
            session=sample_session_data["session"],
            invite_limit=sample_session_data["invite_limit"],
            like_limit=sample_session_data["like_limit"],
            comment_limit=sample_session_data["comment_limit"],
            action_types=sample_session_data["action_types"],
        )

        # Unlock was still called in finally block
        mock_conn.execute.assert_awaited_once()
        unlock_call_arg = mock_conn.execute.call_args[0][0]
        assert "pg_advisory_unlock" in unlock_call_arg

        # Connection was closed
        mock_conn.close.assert_awaited_once()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST F: NO PRODUCTION IN-MEMORY FALLBACK (DATABASE_URL UNSET)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_f_no_fallback_when_database_url_not_configured():
    """In production default (allow_in_memory=False), unconfigured DATABASE_URL fails closed."""
    brand_id = str(uuid4())
    lock = BrandAdvisoryLock(brand_id)  # allow_in_memory defaults to False

    with patch.object(settings, "DATABASE_URL", None):
        acquired = await lock.acquire()
        assert acquired is False
        assert brand_id not in _PROCESS_LOCKS


@pytest.mark.asyncio
async def test_g_explicit_in_memory_allowed_only_when_flagged():
    """In-memory lock is allowed only when explicitly requested (for dev/unit testing)."""
    brand_id = str(uuid4())
    lock = BrandAdvisoryLock(brand_id, allow_in_memory=True)

    with patch.object(settings, "DATABASE_URL", None):
        acquired = await lock.acquire()
        assert acquired is True
        await lock.release()
