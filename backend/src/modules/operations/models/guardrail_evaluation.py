"""Guardrail evaluation models."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from ..constants import ComparisonOp, GuardrailSeverity


@dataclass
class GuardrailRule:
    """Definition of a single guardrail rule."""

    name: str = ""
    description: str = ""
    metric: str = ""
    operator: ComparisonOp = ComparisonOp.GT
    threshold: float = 0.0
    severity: GuardrailSeverity = GuardrailSeverity.WARNING
    enabled: bool = True
    config: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "metric": self.metric,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "enabled": self.enabled,
        }


@dataclass
class GuardrailEvaluation:
    """Result of a single guardrail rule check."""

    id: UUID = field(default_factory=uuid4)
    workflow_id: str = ""
    rule_name: str = ""
    rule_severity: GuardrailSeverity = GuardrailSeverity.INFO
    passed: bool = True
    actual_value: float = 0.0
    threshold_value: float = 0.0
    violation_message: str | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "workflow_id": self.workflow_id,
            "rule_name": self.rule_name,
            "rule_severity": self.rule_severity.value,
            "passed": self.passed,
            "actual_value": self.actual_value,
            "threshold_value": self.threshold_value,
            "violation_message": self.violation_message,
            "evaluated_at": self.evaluated_at.isoformat(),
        }
