from unittest.mock import MagicMock, patch

import pytest

from src.modules.linkedin.worker.action_ledger import ActionLedger


@pytest.fixture
def mock_supabase():
    with patch("src.modules.linkedin.worker.action_ledger.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.mark.asyncio
async def test_action_ledger_acquire_success(mock_supabase):
    # Simulate DB returning a current count of 6 after increment
    mock_rpc = MagicMock()
    mock_rpc.execute.return_value = MagicMock(data=[{"action_count": 6}])
    mock_supabase.rpc.return_value = mock_rpc

    ledger = ActionLedger()

    # Try to acquire with a limit of 10. Should succeed (5 < 10).
    result = await ledger.try_acquire("test_account", "like", 10, "UTC")

    assert result is True
    # Verify that rpc was called
    mock_supabase.rpc.assert_called_once()
    assert mock_supabase.rpc.call_args[0][0] == "exec_sql"


@pytest.mark.asyncio
async def test_action_ledger_acquire_failure_over_limit(mock_supabase):
    # Simulate DB returning empty data because WHERE clause failed
    mock_rpc = MagicMock()
    mock_rpc.execute.return_value = MagicMock(data=[])
    mock_supabase.rpc.return_value = mock_rpc

    ledger = ActionLedger()

    # Try to acquire with a limit of 10. Should fail (10 >= 10).
    result = await ledger.try_acquire("test_account", "like", 10, "UTC")

    assert result is False
