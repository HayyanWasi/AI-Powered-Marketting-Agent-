from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.modules.linkedin.models import CircuitState
from src.modules.linkedin.worker.circuit_breaker import CircuitBreaker


@pytest.fixture
def mock_supabase():
    with patch("src.modules.linkedin.worker.circuit_breaker.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


def test_circuit_breaker_initial_state(mock_supabase):
    # Setup mock to return no existing state
    mock_supabase.table().select().eq().limit().execute.return_value = MagicMock(data=[])

    cb = CircuitBreaker("test_account")
    assert cb.can_proceed() is True
    assert cb._state == CircuitState.CLOSED

    # Verify it created initial state in DB (but only _persist_state calls upsert)
    # The loaded state on init doesn't write unless we tripped or something
    # Actually wait, _persist_state is not called on init unless needed.
    # We can just assert the state.


def test_circuit_breaker_trip(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value = MagicMock(data=[])
    cb = CircuitBreaker("test_account")

    cb.trip("rate_limited", 4.0)

    assert cb._state == CircuitState.OPEN
    assert not cb.can_proceed()
    assert (
        cb._cooldown_until is not None
        if hasattr(cb, "_cooldown_until")
        else cb._cooldown_hours == 4.0
    )

    # Verify it saved the tripped state to DB
    assert mock_supabase.table().upsert.call_count >= 1


def test_circuit_breaker_half_open_transition(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value = MagicMock(data=[])
    cb = CircuitBreaker("test_account")

    # Force trip but put cooldown in the past
    cb._state = CircuitState.OPEN
    cb._tripped_at = datetime.now(UTC) - timedelta(hours=10)

    # Because cooldown elapsed, it should allow one try and transition to half open
    assert cb.can_proceed() is True
    assert cb._state == CircuitState.HALF_OPEN


def test_circuit_breaker_record_success(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value = MagicMock(data=[])
    cb = CircuitBreaker("test_account")

    cb._state = CircuitState.HALF_OPEN
    cb.record_success()

    assert cb._state == CircuitState.CLOSED
    assert cb._consecutive_failures == 0
