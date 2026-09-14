from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.modules.linkedin.models import WarmupPhase
from src.modules.linkedin.worker.warmup_manager import WarmupManager


@pytest.fixture
def mock_supabase():
    with patch("src.modules.linkedin.worker.warmup_manager.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


def test_warmup_manager_baseline_no_increase(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value = MagicMock(
        data=[
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "account_id": "test",
                "activation_date": (datetime.now(UTC) - timedelta(days=10)).date().isoformat(),
                "days_active": 5,
                "current_daily_invite_limit": 5,
                "current_daily_engage_limit": 5,
                "phase": WarmupPhase.BASELINE.value,
                "last_limit_increase_date": (datetime.now(UTC) - timedelta(days=10))
                .date()
                .isoformat(),
            }
        ]
    )

    manager = WarmupManager("test")
    state = manager.evaluate_daily_limits(20, 20)

    # Baseline phase should not automatically increase limits
    assert state.current_daily_invite_limit == 5
    assert state.current_daily_engage_limit == 5
    assert state.phase == WarmupPhase.BASELINE


def test_warmup_manager_ramp_up_increase(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value = MagicMock(
        data=[
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "account_id": "test2",
                "activation_date": (datetime.now(UTC) - timedelta(days=15)).date().isoformat(),
                "days_active": 10,
                "current_daily_invite_limit": 5,
                "current_daily_engage_limit": 5,
                "phase": WarmupPhase.RAMP_UP.value,
                # Last increase was 8 days ago
                "last_limit_increase_date": (datetime.now(UTC) - timedelta(days=8))
                .date()
                .isoformat(),
            }
        ]
    )

    manager = WarmupManager("test2")
    state = manager.evaluate_daily_limits(20, 20)

    # Should have increased by +3 invites and +5 engages
    assert state.current_daily_invite_limit == 8
    assert state.current_daily_engage_limit == 10
    assert state.phase == WarmupPhase.RAMP_UP
    assert mock_supabase.table().upsert.called


def test_warmup_manager_transition_to_operating(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value = MagicMock(
        data=[
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "account_id": "test3",
                "activation_date": (datetime.now(UTC) - timedelta(days=30)).date().isoformat(),
                "days_active": 25,
                "current_daily_invite_limit": 18,
                "current_daily_engage_limit": 18,
                "phase": WarmupPhase.RAMP_UP.value,
                # Last increase was 8 days ago
                "last_limit_increase_date": (datetime.now(UTC) - timedelta(days=8))
                .date()
                .isoformat(),
            }
        ]
    )

    manager = WarmupManager("test3")
    state = manager.evaluate_daily_limits(20, 20)

    # Limit should cap at targets and transition to OPERATING
    assert state.current_daily_invite_limit == 20
    assert state.current_daily_engage_limit == 20
    assert state.phase == WarmupPhase.OPERATING
