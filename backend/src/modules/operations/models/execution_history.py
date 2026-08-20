"""Execution history record model."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from ..constants import ExecutionStatus


@dataclass
class ExecutionHistoryRecord:
    """Searchable record of a completed workflow execution."""

    id: UUID = field(default_factory=uuid4)
    workflow_id: str = ""
    workflow_type: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    trace_id: UUID | None = None
    guardrail_summary: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": str(self.id),
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "total_cost_usd": self.total_cost_usd,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at.isoformat(),
        }
        if self.start_time:
            d["start_time"] = self.start_time.isoformat()
        if self.end_time:
            d["end_time"] = self.end_time.isoformat()
        if self.tags:
            d["tags"] = self.tags
        if self.metadata:
            d["metadata"] = self.metadata
        if self.trace_id:
            d["trace_id"] = str(self.trace_id)
        if self.guardrail_summary:
            d["guardrail_summary"] = self.guardrail_summary
        return d
