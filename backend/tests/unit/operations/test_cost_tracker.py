"""Unit tests for CostTracker."""

from uuid import UUID

from src.modules.operations.services.cost_tracker import CostTracker


class TestCostTracker:
    def test_record_ai_call_returns_record(self):
        tracker = CostTracker()
        record = tracker.record_ai_call(
            workflow_id="wf-001",
            prompt_version_id=UUID(int=1),
            prompt_name="test",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            cost_per_input_token=0.00003,
            cost_per_output_token=0.00006,
            latency_ms=500,
        )
        assert record.workflow_id == "wf-001"
        assert record.total_tokens == 150
        expected_cost = 100 * 0.00003 + 50 * 0.00006
        assert record.estimated_cost_usd == round(expected_cost, 6)

    def test_get_workflow_cost_aggregates(self):
        tracker = CostTracker()
        tracker.record_ai_call(
            "wf-001", UUID(int=1), "p1", "gpt-4", "v1", "openai", 100, 50, 0.01, 0.02, 100
        )
        tracker.record_ai_call(
            "wf-001", UUID(int=2), "p2", "gpt-4", "v1", "openai", 200, 100, 0.01, 0.02, 200
        )
        result = tracker.get_workflow_cost("wf-001")
        assert result["call_count"] == 2
        assert result["total_tokens"] == 450

    def test_get_workflow_cost_returns_zero_for_unknown(self):
        tracker = CostTracker()
        result = tracker.get_workflow_cost("unknown")
        assert result["total_cost_usd"] == 0.0
        assert result["total_tokens"] == 0

    def test_clear_workflow(self):
        tracker = CostTracker()
        tracker.record_ai_call(
            "wf-001", UUID(int=1), "p1", "gpt-4", "v1", "openai", 10, 10, 0.01, 0.02, 50
        )
        tracker.clear_workflow("wf-001")
        result = tracker.get_workflow_cost("wf-001")
        assert result["total_tokens"] == 0
