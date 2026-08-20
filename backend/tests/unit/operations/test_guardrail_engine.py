"""Unit tests for GuardrailEngine."""

from src.modules.operations.constants import ComparisonOp, GuardrailSeverity
from src.modules.operations.models.guardrail_evaluation import GuardrailRule
from src.modules.operations.services.guardrail_engine import (
    GuardrailEngine,
)


class TestGuardrailEngine:
    def test_evaluate_cost_above_threshold(self):
        engine = GuardrailEngine()
        results = engine.evaluate(
            workflow_id="wf-001",
            actual_values={"total_cost_usd": 5.0, "latency_ms": 100, "total_tokens": 50},
        )
        cost_results = [r for r in results if r.rule_name == "cost.max_budget_per_workflow"]
        assert len(cost_results) == 1
        assert not cost_results[0].passed

    def test_evaluate_cost_below_threshold(self):
        engine = GuardrailEngine()
        results = engine.evaluate(
            workflow_id="wf-001",
            actual_values={"total_cost_usd": 0.5, "latency_ms": 100, "total_tokens": 50},
        )
        cost_results = [r for r in results if r.rule_name == "cost.max_budget_per_workflow"]
        assert cost_results[0].passed

    def test_evaluate_deprecated_model(self):
        engine = GuardrailEngine()
        results = engine.evaluate(
            workflow_id="wf-001",
            actual_values={
                "total_cost_usd": 0.1,
                "latency_ms": 100,
                "total_tokens": 50,
                "model_version": "gpt-4-old",
            },
            deprecated_models=["gpt-4-old"],
        )
        dep_results = [r for r in results if r.rule_name == "model.deprecated_version"]
        assert len(dep_results) == 1
        assert not dep_results[0].passed

    def test_add_custom_rule(self):
        engine = GuardrailEngine()
        rule = GuardrailRule(
            name="custom.test",
            description="Custom rule",
            metric="total_tokens",
            operator=ComparisonOp.GT,
            threshold=99999,
            severity=GuardrailSeverity.CRITICAL,
        )
        engine.add_rule(rule)
        rules = engine.get_rules()
        assert any(r.name == "custom.test" for r in rules)

    def test_remove_rule(self):
        engine = GuardrailEngine()
        engine.remove_rule("cost.max_budget_per_workflow")
        results = engine.evaluate(
            workflow_id="wf-001",
            actual_values={"total_cost_usd": 5.0, "latency_ms": 100, "total_tokens": 50},
        )
        assert not any(r.rule_name == "cost.max_budget_per_workflow" for r in results)

    def test_disabled_rule_is_skipped(self):
        engine = GuardrailEngine()
        engine.set_rule_enabled("cost.max_budget_per_workflow", False)
        results = engine.evaluate(
            workflow_id="wf-001",
            actual_values={"total_cost_usd": 5.0, "latency_ms": 100, "total_tokens": 50},
        )
        assert not any(r.rule_name == "cost.max_budget_per_workflow" for r in results)

    def test_evaluation_failure_does_not_crash(self):
        engine = GuardrailEngine()
        results = engine.evaluate(
            workflow_id="wf-001",
            actual_values={},
        )
        assert isinstance(results, list)
