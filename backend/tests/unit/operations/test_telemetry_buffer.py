"""Unit tests for TelemetryBuffer."""

import pytest

from src.modules.operations.services.telemetry_buffer import (
    TelemetryBuffer,
)


class TestTelemetryBuffer:
    @pytest.mark.asyncio
    async def test_enqueue_and_size(self):
        buffer = TelemetryBuffer(name="test", maxsize=100)
        await buffer.enqueue("item1")
        assert buffer.size == 1
        await buffer.enqueue("item2")
        assert buffer.size == 2

    @pytest.mark.asyncio
    async def test_drop_oldest_when_full(self):
        buffer = TelemetryBuffer(name="test", maxsize=3)
        await buffer.enqueue("a")
        await buffer.enqueue("b")
        await buffer.enqueue("c")
        success, dropped = await buffer.enqueue("d")
        assert buffer.size == 3
        assert dropped == 1

    @pytest.mark.asyncio
    async def test_flush_empty_buffer(self):
        buffer = TelemetryBuffer(name="test", maxsize=100)
        flushed = await buffer.flush()
        assert flushed == 0

    @pytest.mark.asyncio
    async def test_fill_pct(self):
        buffer = TelemetryBuffer(name="test", maxsize=10)
        assert buffer.fill_pct == 0.0
        for _ in range(5):
            await buffer.enqueue("x")
        assert buffer.fill_pct == 50.0

    @pytest.mark.asyncio
    async def test_dropped_count(self):
        buffer = TelemetryBuffer(name="test", maxsize=2)
        await buffer.enqueue("a")
        await buffer.enqueue("b")
        await buffer.enqueue("c")
        assert buffer.dropped_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_enqueue(self):
        buffer = TelemetryBuffer(name="test", maxsize=100)

        async def enqueue_many(n: int):
            for i in range(n):
                await buffer.enqueue(f"item-{i}")

        import asyncio

        tasks = [enqueue_many(10) for _ in range(5)]
        await asyncio.gather(*tasks)
        assert buffer.size == 50
