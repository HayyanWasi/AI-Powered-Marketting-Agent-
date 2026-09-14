"""Rate Limiter — Erratic delays between LinkedIn API calls.

All delays use ``await asyncio.sleep()`` so the event loop is never blocked.
Delays are cryptographically random to avoid pattern detection.
"""

from __future__ import annotations

import asyncio
import logging
import random
import secrets

logger = logging.getLogger(__name__)

# Bounds in seconds
_ACTION_DELAY_MIN = 40
_ACTION_DELAY_MAX = 180
_ACTION_JITTER_SIGMA = 15  # Gaussian jitter standard deviation

_MICRO_DELAY_MIN = 2
_MICRO_DELAY_MAX = 8


class RateLimiter:
    """Enforces human-like erratic delays between LinkedIn API calls.

    - ``delay_between_actions()``: 40–180 seconds between distinct actions
    - ``micro_delay()``: 2–8 seconds for sub-actions within a burst
    - All delays are non-blocking (``asyncio.sleep``)
    """

    async def delay_between_actions(self) -> float:
        """Wait 40–180 seconds with Gaussian jitter. Returns chosen delay.

        Uses ``secrets.randbelow()`` for a cryptographically random base
        and adds Gaussian jitter to avoid uniform distribution patterns.
        """
        base = _ACTION_DELAY_MIN + secrets.randbelow(_ACTION_DELAY_MAX - _ACTION_DELAY_MIN + 1)
        jitter = random.gauss(0, _ACTION_JITTER_SIGMA)
        delay = max(_ACTION_DELAY_MIN, min(_ACTION_DELAY_MAX, base + jitter))

        logger.debug("Rate limiter: waiting %.1f seconds between actions", delay)
        await asyncio.sleep(delay)
        return delay

    async def micro_delay(self) -> float:
        """Wait 2–8 seconds for sub-actions within a single burst.

        Used between rapid-fire actions like viewing a profile then
        liking their post — the short gap mimics a human scrolling.
        """
        delay = _MICRO_DELAY_MIN + secrets.randbelow(_MICRO_DELAY_MAX - _MICRO_DELAY_MIN + 1)
        logger.debug("Rate limiter: micro delay %.1f seconds", delay)
        await asyncio.sleep(delay)
        return delay
