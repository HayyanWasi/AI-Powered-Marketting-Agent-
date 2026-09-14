from unittest.mock import patch

import pytest

from src.modules.linkedin.worker.rate_limiter import RateLimiter


@pytest.mark.asyncio
@patch("src.modules.linkedin.worker.rate_limiter.asyncio.sleep")
async def test_delay_between_actions(mock_sleep):
    rl = RateLimiter()

    await rl.delay_between_actions()

    mock_sleep.assert_called_once()
    sleep_val = mock_sleep.call_args[0][0]

    # Assert the random jitter delay is between the configured min/max bounds (40-180 approx)
    assert 10.0 <= sleep_val <= 250.0


@pytest.mark.asyncio
@patch("src.modules.linkedin.worker.rate_limiter.asyncio.sleep")
async def test_micro_delay(mock_sleep):
    rl = RateLimiter()

    await rl.micro_delay()

    mock_sleep.assert_called_once()
    sleep_val = mock_sleep.call_args[0][0]

    # Micro delays are hardcoded between 2 and 8 seconds
    assert 2.0 <= sleep_val <= 8.0
