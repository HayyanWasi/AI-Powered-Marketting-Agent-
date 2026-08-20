"""Telemetry event model for structured JSON logging."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..constants import TelemetryEventType


@dataclass
class TelemetryEvent:
    """A structured telemetry event emitted as JSON log."""

    event_type: TelemetryEventType = TelemetryEventType.WORKFLOW_START
    workflow_id: str = ""
    trace_id: str | None = None
    duration_ms: int | None = None
    level: str = "INFO"
    message: str = ""
    metadata: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "event_type": self.event_type.value,
            "workflow_id": self.workflow_id,
            "message": self.message,
        }
        if self.trace_id:
            d["trace_id"] = self.trace_id
        if self.duration_ms is not None:
            d["duration_ms"] = self.duration_ms
        if self.metadata:
            d["metadata"] = self.metadata
        return d
