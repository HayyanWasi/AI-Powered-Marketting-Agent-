"""Bounded telemetry buffer with async flush and exponential backoff."""

import asyncio
import time
from asyncio import Task
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from ..constants import (
    TELEMETRY_BUFFER_MAXSIZE,
    TELEMETRY_RETRY_BASE_DELAY_S,
    TELEMETRY_RETRY_MAX_DELAY_S,
)


@dataclass
class BufferItem:
    """An item in the telemetry buffer."""

    data: Any
    enqueued_at: float = field(default_factory=time.time)
    retry_count: int = 0


class TelemetryBuffer:
    """Bounded queue buffer for telemetry data with async flush and retry.

    Buffers telemetry items (LangSmith traces, OTel spans, log entries)
    when backends are unavailable. Uses a drop-oldest policy when full.
    Flushes asynchronously with exponential backoff.

    Args:
        name: Human-readable buffer name for logging.
        maxsize: Maximum number of items in the buffer.
        flush_fn: Async callable to flush a single item. Returns True
            on success, False on failure.
    """

    def __init__(
        self,
        name: str,
        maxsize: int = TELEMETRY_BUFFER_MAXSIZE,
        flush_fn: Callable[[Any], Awaitable[bool]] | None = None,
    ) -> None:
        self._name = name
        self._maxsize = maxsize
        self._flush_fn = flush_fn
        self._queue: deque[BufferItem] = deque(maxlen=maxsize)
        self._dropped_count: int = 0
        self._retry_count: int = 0
        self._flush_task: Task[Any] | None = None
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def fill_pct(self) -> float:
        return (len(self._queue) / self._maxsize) * 100 if self._maxsize > 0 else 0.0

    async def enqueue(self, item: Any) -> tuple[bool, int]:
        """Add an item to the buffer.

        If the buffer is full, the oldest item is dropped.

        Args:
            item: The telemetry data to buffer.

        Returns:
            Tuple of (success, dropped_count).
        """
        async with self._lock:
            dropped = 0
            if len(self._queue) >= self._maxsize:
                self._queue.popleft()
                dropped = 1
                self._dropped_count += 1
            self._queue.append(BufferItem(data=item))
            return True, dropped

    async def flush(self) -> int:
        """Flush all buffered items by calling flush_fn on each.

        Items that fail remain in the queue for the next flush cycle.
        Uses exponential backoff per item.

        Returns:
            Number of items successfully flushed.
        """
        if not self._flush_fn:
            return 0

        async with self._lock:
            items = list(self._queue)
            self._queue.clear()

        flushed = 0
        remaining: list[BufferItem] = []

        for item in items:
            try:
                success = await self._flush_fn(item.data)
                if success:
                    flushed += 1
                else:
                    item.retry_count += 1
                    self._retry_count += 1
                    remaining.append(item)
            except Exception:
                item.retry_count += 1
                self._retry_count += 1
                remaining.append(item)

        async with self._lock:
            for item in remaining:
                if len(self._queue) < self._maxsize:
                    self._queue.append(item)
                else:
                    self._dropped_count += 1

        return flushed

    async def flush_with_backoff(self, max_retries: int = 3) -> int:
        """Flush with exponential backoff retry.

        Args:
            max_retries: Maximum retry attempts per flush cycle.

        Returns:
            Number of items successfully flushed.
        """
        total_flushed = 0
        delay = TELEMETRY_RETRY_BASE_DELAY_S

        for attempt in range(max_retries):
            flushed = await self.flush()
            total_flushed += flushed

            if self.size == 0:
                break

            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay = min(delay * 2, TELEMETRY_RETRY_MAX_DELAY_S)

        return total_flushed

    async def start_auto_flush(self, interval_s: float = 5.0) -> None:
        """Start a background task that flushes periodically.

        Args:
            interval_s: Seconds between flush cycles.
        """
        if self._flush_task is not None:
            return

        async def _loop() -> None:
            while True:
                await asyncio.sleep(interval_s)
                if self.size > 0:
                    await self.flush_with_backoff()

        self._flush_task = asyncio.create_task(_loop())

    async def stop_auto_flush(self) -> None:
        """Stop the background flush task."""
        if self._flush_task is not None:
            self._flush_task.cancel()
            self._flush_task = None
