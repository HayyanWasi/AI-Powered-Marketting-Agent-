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

    # Verify query used canonical linkedin_account_id
    mock_supabase.table().select().eq.assert_called_with("linkedin_account_id", "test_account")


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

    # Verify it saved the tripped state using linkedin_account_id only
    assert mock_supabase.table().upsert.call_count >= 1
    call_args = mock_supabase.table().upsert.call_args
    data = call_args[0][0]
    kwargs = call_args[1]
    assert data["linkedin_account_id"] == "test_account"
    assert "account_id" not in data
    assert kwargs.get("on_conflict") == "linkedin_account_id"


def test_circuit_breaker_load_persisted_state(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value = MagicMock(
        data=[
            {
                "linkedin_account_id": "test_account",
                "state": "open",
                "tripped_at": datetime.now(UTC).isoformat(),
                "trip_reason": "rate_limited",
                "cooldown_hours": 3.0,
            }
        ]
    )

    cb = CircuitBreaker("test_account")
    assert cb._state == CircuitState.OPEN
    assert cb._trip_reason == "rate_limited"
    assert cb._cooldown_hours == 3.0
    mock_supabase.table().select().eq.assert_called_with("linkedin_account_id", "test_account")


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
