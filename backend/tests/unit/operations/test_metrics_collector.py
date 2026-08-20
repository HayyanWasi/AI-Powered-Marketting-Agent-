"""Unit tests for MetricsCollector."""

import time

from src.modules.operations.services.metrics_collector import (
    MetricsCollector,
)


class TestMetricsCollector:
    def test_empty_snapshot(self):
        collector = MetricsCollector(window_s=60)
        snapshot = collector.get_snapshot()
        assert snapshot.total_workflows == 0
        assert snapshot.latency_p50_ms == 0.0

    def test_single_execution(self):
        collector = MetricsCollector(window_s=60)
        collector.record_execution(duration_ms=1000, status="completed")
        snapshot = collector.get_snapshot()
        assert snapshot.total_workflows == 1
        assert snapshot.latency_p50_ms == 1000.0
        assert snapshot.failure_rate == 0.0

    def test_failure_rate(self):
        collector = MetricsCollector(window_s=60)
        collector.record_execution(duration_ms=100, status="completed")
        collector.record_execution(duration_ms=200, status="completed")
        collector.record_execution(duration_ms=300, status="failed")
        snapshot = collector.get_snapshot()
        assert snapshot.total_workflows == 3
        assert snapshot.failure_rate == 1.0 / 3.0

    def test_latency_percentiles(self):
        collector = MetricsCollector(window_s=60)
        for i in range(1, 101):
            collector.record_execution(duration_ms=i * 10, status="completed")
        snapshot = collector.get_snapshot()
        assert snapshot.latency_p50_ms == 505.0
        assert abs(snapshot.latency_p95_ms - 950.5) < 1.0
        assert abs(snapshot.latency_p99_ms - 990.1) < 1.0

    def test_window_expiry(self):
        collector = MetricsCollector(window_s=0.1)
        collector.record_execution(duration_ms=100, status="completed")
        time.sleep(0.2)
        snapshot = collector.get_snapshot()
        assert snapshot.total_workflows == 0
