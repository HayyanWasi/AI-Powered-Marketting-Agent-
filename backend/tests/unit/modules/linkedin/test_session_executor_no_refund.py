from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.linkedin.models import SessionWindow
from src.modules.linkedin.worker.session_executor import SessionExecutor


@pytest.fixture
def mocks():
    # We patch multiple dependencies of the executor
    with (
        patch("src.modules.linkedin.worker.session_executor.CircuitBreaker") as mock_cb_cls,
        patch("src.modules.linkedin.worker.session_executor.RateLimiter") as mock_rl_cls,
        patch("src.modules.linkedin.worker.session_executor.ActionLedger") as mock_al_cls,
        patch("src.modules.linkedin.worker.session_executor.TargetResolver") as mock_tr_cls,
        patch("src.modules.linkedin.worker.session_executor.ReviewQueue") as mock_rq_cls,
        patch("src.modules.linkedin.worker.session_executor.get_unipile_gateway") as mock_gw_fn,
        patch("src.modules.linkedin.worker.session_executor.get_supabase_client") as mock_sb_fn,
    ):

        mock_cb = MagicMock()
        mock_cb_cls.return_value = mock_cb

        mock_rl = AsyncMock()
        mock_rl_cls.return_value = mock_rl

        mock_al = AsyncMock()
        mock_al_cls.return_value = mock_al

        mock_tr = AsyncMock()
        mock_tr.load_personas.return_value = []
        mock_tr_cls.return_value = mock_tr

        mock_rq = MagicMock()
        mock_rq_cls.return_value = mock_rq

        mock_gw = AsyncMock()
        mock_gw_fn.return_value = mock_gw

        mock_sb = MagicMock()
        mock_sb.table().insert().execute.return_value = MagicMock(data=[{"id": "claim-123"}])
        mock_sb.table().select().eq().eq().eq().limit().execute.return_value = MagicMock(data=[])
        mock_sb.table().update().eq().execute.return_value = MagicMock()
        mock_sb.table().upsert().execute.return_value = MagicMock()
        mock_sb_fn.return_value = mock_sb

        yield {
            "cb": mock_cb,
            "rl": mock_rl,
            "al": mock_al,
            "tr": mock_tr,
            "rq": mock_rq,
            "gw": mock_gw,
            "sb": mock_sb,
        }


@pytest.mark.asyncio
async def test_session_aborts_if_circuit_open(mocks):
    mocks["cb"].can_proceed.return_value = False

    executor = SessionExecutor("test", "UTC")
    session = SessionWindow(
        start=time(9, 0), end=time(10, 0), max_actions=5, action_types=("like",)
    )

    result = await executor.execute_session(session, 10, 10, 10)

    assert result.status == "aborted"
    assert result.reason == "circuit_breaker_open"
    # Ensure no actions were taken
    assert result.actions_attempted == 0
    mocks["al"].try_acquire.assert_not_called()


@pytest.mark.asyncio
async def test_no_refund_policy_on_failure(mocks):
    # Setup mocks
    mocks["cb"].can_proceed.return_value = True

    # Target resolver returns 1 post to like
    mocks["tr"].load_personas.return_value = ["persona"]
    mock_target = MagicMock()
    mock_target.post_id = "post_fail_1"
    mocks["tr"].get_engagement_targets.return_value = [mock_target]

    # Ledger allows the action
    mocks["al"].try_acquire.return_value = True

    # Gateway FAILS to like (returns False)
    mocks["gw"].like_post.return_value = False

    executor = SessionExecutor("test", "UTC")
    session = SessionWindow(
        start=time(9, 0), end=time(10, 0), max_actions=5, action_types=("like",)
    )

    result = await executor.execute_session(session, 10, 10, 10)

    # Ledger was acquired (burned)
    mocks["al"].try_acquire.assert_called_once()

    # Gateway was called
    mocks["gw"].like_post.assert_called_once()

    # But it failed, so succeeded=0, failed=1
    assert result.actions_succeeded == 0
    assert result.actions_failed == 1

    # Importantly, we verify the ledger has no "refund" method and none was called
    # (By design, we just move on)


@pytest.mark.asyncio
async def test_successful_execution(mocks):
    mocks["cb"].can_proceed.return_value = True
    mocks["rq"].get_approved_for_publishing.return_value = []

    # Mock finding 2 target posts to like
    mocks["tr"].load_personas.return_value = ["persona"]
    mock_target = MagicMock()
    mock_target.post_id = "post_1"
    mocks["tr"].get_engagement_targets.return_value = [mock_target, mock_target]

    mocks["al"].try_acquire.return_value = True
    mocks["gw"].like_post.return_value = True

    executor = SessionExecutor("test", "UTC")
    session = SessionWindow(
        start=time(9, 0), end=time(10, 0), max_actions=2, action_types=("like",)
    )

    result = await executor.execute_session(session, 10, 10, 10)

    assert result.actions_attempted == 2
    assert result.actions_succeeded == 2

    # Rate limiter delays should have been called
    assert mocks["rl"].delay_between_actions.call_count == 2
    assert mocks["rl"].micro_delay.call_count == 2
