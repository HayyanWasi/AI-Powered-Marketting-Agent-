"""Distributed Advisory Locking for Multi-Tenant LinkedIn Engagement Automation.

Uses dedicated session-level PostgreSQL advisory locks (pg_try_advisory_lock / pg_advisory_unlock)
when DATABASE_URL is configured.

FAIL-CLOSED INVARIANTS:
1. DB advisory lock acquired -> engagement session may run.
2. pg_try_advisory_lock returns False -> another worker owns lock -> SKIP brand/session.
3. Database connection / lock acquisition raises ANY error:
   - SKIP engagement session immediately (returns False).
   - NEVER fall back to in-memory locking in production.
   - Log clear error and close connection.
4. If lock was acquired:
   - ALWAYS pg_advisory_unlock + conn.close() in release() / finally.
5. Never hold normal DB transaction across:
   - Unipile calls
   - LLM calls
   - network I/O.
   (The connection is checked out dedicated solely for the session advisory lock;
   no BEGIN/COMMIT transaction block is held.)
6. In-memory lock:
   - May exist ONLY for isolated unit tests/dev when explicitly enabled (`allow_in_memory=True`).
   - NEVER acts as an automatic fallback when PostgreSQL advisory locking fails.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import zlib
from typing import Any

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Explicit in-memory lock registry — strictly for isolated unit tests / dev
_PROCESS_LOCKS: dict[str, asyncio.Lock] = {}
_PROCESS_LOCKS_GUARD = asyncio.Lock()


async def _get_brand_process_lock(brand_id: str) -> asyncio.Lock:
    """Return process-level lock for explicit unit-test isolation."""
    async with _PROCESS_LOCKS_GUARD:
        if brand_id not in _PROCESS_LOCKS:
            _PROCESS_LOCKS[brand_id] = asyncio.Lock()
        return _PROCESS_LOCKS[brand_id]


def _stable_lock_key(brand_id: str) -> int:
    """Compute a stable 32-bit signed integer key from brand_id for pg_advisory_lock."""
    raw_crc = zlib.crc32(f"engagement_brand_{brand_id}".encode())
    # Map unsigned 32-bit to signed 32-bit integer (-2^31 to 2^31 - 1)
    if raw_crc >= 0x80000000:
        return raw_crc - 0x100000000
    return raw_crc


class BrandAdvisoryLock:
    """Acquires a dedicated session-level advisory lock for a brand during engagement.

    Enforces strict fail-closed behavior: errors during DB connection or lock
    acquisition fail closed (returning False) and will NEVER fall back to in-memory
    locking in production.
    """

    def __init__(self, brand_id: str, *, allow_in_memory: bool = False) -> None:
        self.brand_id = str(brand_id)
        self.lock_key = _stable_lock_key(self.brand_id)
        self.allow_in_memory = allow_in_memory
        self._conn: Any = None
        self._process_locked = False

    async def acquire(self) -> bool:
        """Attempt to acquire non-blocking lock.

        Returns:
            True if lock was successfully acquired, False otherwise.
            Fails closed on ANY database error.
        """
        if settings.DATABASE_URL:
            try:
                import asyncpg  # type: ignore

                self._conn = await asyncpg.connect(settings.DATABASE_URL, timeout=10.0)
                locked = await self._conn.fetchval("SELECT pg_try_advisory_lock($1)", self.lock_key)
                if not locked:
                    logger.info(
                        "Advisory lock unavailable for brand %s (held by another worker); skipping session",
                        self.brand_id,
                    )
                    await self._conn.close()
                    self._conn = None
                    return False

                logger.debug("Acquired PostgreSQL advisory lock for brand %s", self.brand_id)
                return True
            except Exception as e:
                logger.error(
                    "PostgreSQL advisory lock acquisition failed for brand %s: %s; failing closed (zero engagement actions, NO in-memory fallback)",
                    self.brand_id,
                    e,
                )
                if self._conn:
                    with contextlib.suppress(Exception):
                        await self._conn.close()
                    self._conn = None
                # FAIL CLOSED: Never fall back to in-memory lock when DB acquisition fails
                return False

        # In-memory lock is strictly restricted to isolated unit tests/dev with explicit opt-in
        if self.allow_in_memory:
            lock = await _get_brand_process_lock(self.brand_id)
            if lock.locked():
                logger.info("Process lock unavailable for brand %s", self.brand_id)
                return False
            await lock.acquire()
            self._process_locked = True
            logger.debug(
                "Acquired in-memory lock for brand %s (explicit test/dev mode)", self.brand_id
            )
            return True

        logger.error(
            "DATABASE_URL not configured and in-memory fallback disabled for brand %s; failing closed (zero engagement actions)",
            self.brand_id,
        )
        return False

    async def release(self) -> None:
        """Release the acquired lock in finally block."""
        if self._conn is not None:
            try:
                await self._conn.execute("SELECT pg_advisory_unlock($1)", self.lock_key)
                logger.debug("Released PostgreSQL advisory lock for brand %s", self.brand_id)
            except Exception as e:
                logger.error("Error releasing advisory lock for brand %s: %s", self.brand_id, e)
            finally:
                with contextlib.suppress(Exception):
                    await self._conn.close()
                self._conn = None

        if self._process_locked:
            try:
                lock = await _get_brand_process_lock(self.brand_id)
                if lock.locked():
                    lock.release()
                logger.debug("Released in-memory lock for brand %s", self.brand_id)
            except Exception as e:
                logger.error("Error releasing in-memory lock for brand %s: %s", self.brand_id, e)
            finally:
                self._process_locked = False

    async def __aenter__(self) -> bool:
        return await self.acquire()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.release()
