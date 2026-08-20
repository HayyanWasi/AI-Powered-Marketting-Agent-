"""AI telemetry record model."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass
class AITelemetryRecord:
    """Single AI request record with cost and version tracking."""

    id: UUID = field(default_factory=uuid4)
    workflow_id: str = ""
    trace_span_id: UUID | None = None
    prompt_version_id: UUID | None = None
    prompt_name: str = ""
    model_name: str = ""
    model_version: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_per_input_token: float = 0.0
    cost_per_output_token: float = 0.0
    estimated_cost_usd: float = 0.0
    latency_ms: int = 0
    status: str = "success"
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self.total_tokens = self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "workflow_id": self.workflow_id,
            "trace_span_id": str(self.trace_span_id) if self.trace_span_id else None,
            "prompt_version_id": str(self.prompt_version_id) if self.prompt_version_id else None,
            "prompt_name": self.prompt_name,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }
