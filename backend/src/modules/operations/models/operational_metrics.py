"""Operational metrics models."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class MetricPoint:
    """A single data point in a metric time series."""

    name: str = ""
    value: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    labels: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.labels:
            d["labels"] = self.labels
        return d


@dataclass
class OperationalMetricsSnapshot:
    """Aggregated operational metrics from a sliding window."""

    window_start: datetime | None = None
    window_end: datetime | None = None
    total_workflows: int = 0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    throughput: float = 0.0
    failure_count: int = 0
    failure_rate: float = 0.0
    total_retries: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_start": self.window_start.isoformat() if self.window_start else None,
            "window_end": self.window_end.isoformat() if self.window_end else None,
            "total_workflows": self.total_workflows,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "throughput": self.throughput,
            "failure_count": self.failure_count,
            "failure_rate": self.failure_rate,
            "total_retries": self.total_retries,
            "total_cost_usd": self.total_cost_usd,
            "total_tokens": self.total_tokens,
        }
