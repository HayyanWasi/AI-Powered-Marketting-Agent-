"""Execution trace models."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from ..constants import ExecutionStatus, SpanStatus, SpanType


@dataclass
class TraceSpan:
    """A single span within an execution trace."""

    span_id: UUID = field(default_factory=uuid4)
    parent_span_id: UUID | None = None
    name: str = ""
    span_type: SpanType = SpanType.CHAIN
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: int | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    status: SpanStatus = SpanStatus.PENDING
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "span_id": str(self.span_id),
            "name": self.name,
            "span_type": self.span_type.value,
            "status": self.status.value,
        }
        if self.parent_span_id:
            d["parent_span_id"] = str(self.parent_span_id)
        if self.start_time:
            d["start_time"] = self.start_time.isoformat()
        if self.end_time:
            d["end_time"] = self.end_time.isoformat()
        if self.duration_ms is not None:
            d["duration_ms"] = self.duration_ms
        if self.input is not None:
            d["input"] = self.input
        if self.output is not None:
            d["output"] = self.output
        if self.metadata is not None:
            d["metadata"] = self.metadata
        if self.error is not None:
            d["error"] = self.error
        return d


@dataclass
class ExecutionTrace:
    """Complete trace of a workflow execution."""

    id: UUID = field(default_factory=uuid4)
    workflow_id: str = ""
    workflow_type: str = ""
    root_span: TraceSpan | None = None
    spans: list[TraceSpan] = field(default_factory=list)
    total_duration_ms: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    status: ExecutionStatus = ExecutionStatus.PENDING
    error: str | None = None
    guardrail_results: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] | None = None
    _root_run: Any = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    user_id: UUID | str | None = None

    def add_span(self, span: TraceSpan) -> None:
        self.spans.append(span)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": str(self.id),
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "spans": [s.to_dict() for s in self.spans],
            "total_duration_ms": self.total_duration_ms,
            "total_cost_usd": self.total_cost_usd,
            "total_tokens": self.total_tokens,
            "status": self.status.value,
            "error": self.error,
            "guardrail_results": [
                r.to_dict() if hasattr(r, "to_dict") else r for r in self.guardrail_results
            ],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
        if self.user_id:
            d["user_id"] = str(self.user_id)
        return d
