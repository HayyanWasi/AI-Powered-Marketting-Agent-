"""Operational metrics collector with sliding window aggregation."""

import math
import time
from collections import deque
from datetime import UTC, datetime
from typing import Any

from ..models.operational_metrics import OperationalMetricsSnapshot


class MetricsCollector:
    """Collects and aggregates operational metrics from a sliding window.

    Maintains a time-based sliding window (default 60s) of execution
    events and computes p50/p95/p99 latency, throughput, failure rate,
    retry count, token usage, and cost.
    """

    def __init__(self, window_s: int = 60) -> None:
        self._window_s = window_s
        self._events: deque[dict[str, Any]] = deque()

    def record_execution(
        self,
        duration_ms: int,
        status: str,
        total_cost_usd: float = 0.0,
        total_tokens: int = 0,
        retry_count: int = 0,
    ) -> None:
        """Record a workflow execution event.

        Args:
            duration_ms: Execution duration.
            status: 'completed' or status string (non-completed = failure).
            total_cost_usd: Total cost of the workflow.
            total_tokens: Total tokens used.
            retry_count: Number of retries.
        """
        self._events.append(
            {
                "timestamp": time.time(),
                "duration_ms": duration_ms,
                "status": status,
                "total_cost_usd": total_cost_usd,
                "total_tokens": total_tokens,
                "retry_count": retry_count,
            }
        )

    def get_snapshot(self) -> OperationalMetricsSnapshot:
        """Compute a metrics snapshot from the current sliding window.

        Returns:
            OperationalMetricsSnapshot with aggregated values.
        """
        now = time.time()
        cutoff = now - self._window_s

        # Purge expired events
        while self._events and self._events[0]["timestamp"] < cutoff:
            self._events.popleft()

        events = list(self._events)
        if not events:
            return OperationalMetricsSnapshot()

        latencies = sorted(e["duration_ms"] for e in events)
        total = len(events)
        failures = sum(1 for e in events if e["status"] != "completed")
        total_cost = sum(e["total_cost_usd"] for e in events)
        total_tokens = sum(e["total_tokens"] for e in events)
        total_retries = sum(e["retry_count"] for e in events)

        return OperationalMetricsSnapshot(
            window_start=datetime.fromtimestamp(cutoff, tz=UTC),
            window_end=datetime.fromtimestamp(now, tz=UTC),
            total_workflows=total,
            latency_p50_ms=self._percentile(latencies, 50),
            latency_p95_ms=self._percentile(latencies, 95),
            latency_p99_ms=self._percentile(latencies, 99),
            throughput=total / (self._window_s / 60.0),
            failure_count=failures,
            failure_rate=failures / total if total > 0 else 0.0,
            total_retries=total_retries,
            total_cost_usd=total_cost,
            total_tokens=total_tokens,
        )

    @staticmethod
    def _percentile(sorted_data: list[float], percentile: float) -> float:
        """Compute the percentile from a sorted list.

        Args:
            sorted_data: Sorted list of values.
            percentile: Percentile to compute (0-100).

        Returns:
            Computed percentile value.
        """
        if not sorted_data:
            return 0.0
        k = (percentile / 100.0) * (len(sorted_data) - 1)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_data[int(k)]
        return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)
