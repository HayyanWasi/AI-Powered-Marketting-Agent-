"""Operational guardrail engine — rule-based evaluation without blocking."""

from typing import Any
from uuid import uuid4

from ..constants import ComparisonOp, GuardrailSeverity
from ..errors import GuardrailEvaluationError
from ..models.guardrail_evaluation import GuardrailEvaluation, GuardrailRule


class GuardrailEngine:
    """Rule-based guardrail evaluation engine.

    Evaluates operational policies (cost, latency, model version, tokens)
    against workflow execution data. Evaluation is non-blocking — results
    are recorded but never interrupt workflow execution.
    """

    def __init__(self) -> None:
        self._rules: list[GuardrailRule] = []
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load the default set of guardrail rules."""
        self._rules = [
            GuardrailRule(
                name="cost.max_budget_per_workflow",
                description="Workflow cost exceeds maximum budget",
                metric="total_cost_usd",
                operator=ComparisonOp.GT,
                threshold=1.0,
                severity=GuardrailSeverity.WARNING,
                enabled=True,
            ),
            GuardrailRule(
                name="model.deprecated_version",
                description="Workflow uses a deprecated model version",
                metric="model_version",
                operator=ComparisonOp.IN,
                threshold=0.0,
                severity=GuardrailSeverity.WARNING,
                enabled=True,
            ),
            GuardrailRule(
                name="latency.max_slo",
                description="Workflow latency exceeds SLO",
                metric="latency_ms",
                operator=ComparisonOp.GT,
                threshold=60000,
                severity=GuardrailSeverity.INFO,
                enabled=True,
            ),
            GuardrailRule(
                name="tokens.max_per_workflow",
                description="Total tokens exceed workflow limit",
                metric="total_tokens",
                operator=ComparisonOp.GT,
                threshold=100000,
                severity=GuardrailSeverity.INFO,
                enabled=True,
            ),
        ]

    def get_rules(self) -> list[GuardrailRule]:
        """Get all registered guardrail rules.

        Returns:
            List of GuardrailRule instances.
        """
        return list(self._rules)

    def add_rule(self, rule: GuardrailRule) -> None:
        """Add a custom guardrail rule.

        Args:
            rule: The guardrail rule to add.
        """
        self._rules.append(rule)

    def remove_rule(self, rule_name: str) -> None:
        """Remove a guardrail rule by name.

        Args:
            rule_name: Name of the rule to remove.
        """
        self._rules = [r for r in self._rules if r.name != rule_name]

    def set_rule_enabled(self, rule_name: str, enabled: bool) -> None:
        """Enable or disable a guardrail rule.

        Args:
            rule_name: Name of the rule.
            enabled: Whether the rule should be active.
        """
        for rule in self._rules:
            if rule.name == rule_name:
                rule.enabled = enabled
                break

    def evaluate(
        self,
        workflow_id: str,
        actual_values: dict[str, Any],
        deprecated_models: list[str] | None = None,
    ) -> list[GuardrailEvaluation]:
        """Evaluate guardrail rules against workflow execution data.

        Args:
            workflow_id: Workflow execution identifier.
            actual_values: Dict of metric_name -> actual_value. Expected
                keys: total_cost_usd, latency_ms, total_tokens, model_version.
            deprecated_models: Optional list of deprecated model version strings.

        Returns:
            List of GuardrailEvaluation results. Empty if no rules fire.

        Raises:
            GuardrailEvaluationError: If evaluation itself fails.
        """
        results: list[GuardrailEvaluation] = []

        try:
            for rule in self._rules:
                if not rule.enabled:
                    continue

                actual = self._get_actual_value(actual_values, rule.metric)
                if actual is None:
                    continue

                passed = self._evaluate_rule(rule, actual, deprecated_models or [])

                violation_message: str | None = None
                if not passed:
                    violation_message = (
                        f"Guardrail '{rule.name}': value {actual} "
                        f"violates threshold {rule.threshold} "
                        f"(op={rule.operator.value})"
                    )

                evaluation = GuardrailEvaluation(
                    id=uuid4(),
                    workflow_id=workflow_id,
                    rule_name=rule.name,
                    rule_severity=rule.severity,
                    passed=passed,
                    actual_value=float(actual) if not isinstance(actual, str) else 0.0,
                    threshold_value=rule.threshold,
                    violation_message=violation_message,
                )
                results.append(evaluation)

        except Exception as e:
            raise GuardrailEvaluationError(
                f"Guardrail evaluation failed for workflow {workflow_id}: {e}"
            ) from e

        return results

    @staticmethod
    def _get_actual_value(
        actual_values: dict[str, Any],
        metric: str,
    ) -> Any:
        """Extract the actual value for a given metric.

        Args:
            actual_values: Dict of metric_name -> value.
            metric: The metric key to extract.

        Returns:
            The actual value, or None if not found.
        """
        if metric == "model_version":
            return actual_values.get("model_version")
        return actual_values.get(metric)

    @staticmethod
    def _evaluate_rule(
        rule: GuardrailRule,
        actual: Any,
        deprecated_models: list[str],
    ) -> bool:
        """Evaluate a single rule against an actual value.

        Args:
            rule: The guardrail rule to evaluate.
            actual: The observed value.
            deprecated_models: List of deprecated model versions.

        Returns:
            True if the rule passes (no violation), False otherwise.
        """
        if rule.metric == "model_version":
            if isinstance(actual, str):
                return actual not in deprecated_models
            return True

        if not isinstance(actual, (int, float)):
            return True

        if rule.operator == ComparisonOp.GT:
            return actual <= rule.threshold
        elif rule.operator == ComparisonOp.GTE:
            return actual < rule.threshold
        elif rule.operator == ComparisonOp.LT:
            return actual >= rule.threshold
        elif rule.operator == ComparisonOp.LTE:
            return actual > rule.threshold
        elif rule.operator == ComparisonOp.EQ:
            return actual == rule.threshold
        elif rule.operator == ComparisonOp.IN:
            return actual in rule.config.get("allowed_values", []) if rule.config else True
        return True
