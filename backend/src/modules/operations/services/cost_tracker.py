"""Token and cost tracker for AI request telemetry."""

from typing import Any
from uuid import UUID, uuid4

from ..models.ai_telemetry import AITelemetryRecord


class CostTracker:
    """Tracks token usage and computes cost estimates for AI requests.

    Receives per-call token counts and model info, computes costs,
    and emits AITelemetryRecord instances. Supports per-workflow
    cost aggregation.
    """

    def __init__(self) -> None:
        self._workflow_costs: dict[str, dict[str, Any]] = {}

    def record_ai_call(
        self,
        workflow_id: str,
        prompt_version_id: UUID | None,
        prompt_name: str,
        model_name: str,
        model_version: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        cost_per_input_token: float,
        cost_per_output_token: float,
        latency_ms: int,
        status: str = "success",
        error_message: str | None = None,
    ) -> AITelemetryRecord:
        """Record a single AI call and compute its cost.

        Args:
            workflow_id: Workflow execution identifier.
            prompt_version_id: Immutable prompt version UUID.
            prompt_name: Human-readable prompt name.
            model_name: Model identifier.
            model_version: Model version string.
            provider: Provider name.
            input_tokens: Input token count.
            output_tokens: Output token count.
            cost_per_input_token: USD per input token.
            cost_per_output_token: USD per output token.
            latency_ms: Request latency.
            status: Request status.
            error_message: Error details if failed.

        Returns:
            AITelemetryRecord with computed cost.
        """
        total_tokens = input_tokens + output_tokens
        estimated_cost = round(
            (input_tokens * cost_per_input_token) + (output_tokens * cost_per_output_token),
            6,
        )

        record = AITelemetryRecord(
            id=uuid4(),
            workflow_id=workflow_id,
            prompt_version_id=prompt_version_id,
            prompt_name=prompt_name,
            model_name=model_name,
            model_version=model_version,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_per_input_token=cost_per_input_token,
            cost_per_output_token=cost_per_output_token,
            estimated_cost_usd=estimated_cost,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )

        if workflow_id not in self._workflow_costs:
            self._workflow_costs[workflow_id] = {
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "calls": [],
            }
        self._workflow_costs[workflow_id]["total_cost_usd"] += estimated_cost
        self._workflow_costs[workflow_id]["total_tokens"] += total_tokens
        self._workflow_costs[workflow_id]["calls"].append(record)

        return record

    def get_workflow_cost(self, workflow_id: str) -> dict[str, Any]:
        """Get aggregated cost and token data for a workflow.

        Args:
            workflow_id: Workflow execution identifier.

        Returns:
            Dict with total_cost_usd, total_tokens, and call count.
        """
        data = self._workflow_costs.get(
            workflow_id,
            {
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "calls": [],
            },
        )
        return {
            "workflow_id": workflow_id,
            "total_cost_usd": round(data["total_cost_usd"], 6),
            "total_tokens": data["total_tokens"],
            "call_count": len(data["calls"]),
        }

    def clear_workflow(self, workflow_id: str) -> None:
        """Clear cost data for a completed workflow.

        Args:
            workflow_id: Workflow execution identifier.
        """
        self._workflow_costs.pop(workflow_id, None)
