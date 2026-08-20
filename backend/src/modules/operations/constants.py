"""Enums and constants for the Platform & Operations module."""

from enum import StrEnum
from typing import Final


class ExecutionStatus(StrEnum):
    """Status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SpanType(StrEnum):
    """Category of a trace span."""

    WORKFLOW = "workflow"
    CHAIN = "chain"
    LLM = "llm"
    TOOL = "tool"
    RETRY = "retry"


class SpanStatus(StrEnum):
    """Status of an individual span."""

    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"


class GuardrailSeverity(StrEnum):
    """Severity level of a guardrail violation."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ComparisonOp(StrEnum):
    """Comparison operator for guardrail rule evaluation."""

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    IN = "in"


class TelemetryEventType(StrEnum):
    """Type of operational telemetry event."""

    WORKFLOW_START = "workflow.start"
    WORKFLOW_COMPLETE = "workflow.complete"
    WORKFLOW_FAIL = "workflow.fail"
    WORKFLOW_RETRY = "workflow.retry"
    AI_REQUEST_START = "ai.request.start"
    AI_REQUEST_COMPLETE = "ai.request.complete"
    GUARDRAIL_EVALUATION = "guardrail.evaluation"
    TELEMETRY_BUFFER_STATUS = "telemetry.buffer.status"


class MetricName(StrEnum):
    """Names of operational metrics."""

    LATENCY_P50_MS = "latency.p50_ms"
    LATENCY_P95_MS = "latency.p95_ms"
    LATENCY_P99_MS = "latency.p99_ms"
    THROUGHPUT = "throughput"
    FAILURE_RATE = "failure_rate"
    RETRY_COUNT = "retry_count"
    TOTAL_COST_USD = "total_cost_usd"
    TOTAL_TOKENS = "total_tokens"


# Buffer configuration defaults
TELEMETRY_BUFFER_MAXSIZE: Final[int] = 10000
TELEMETRY_BUFFER_DROP_POLICY: Final[str] = "oldest"
TELEMETRY_RETRY_MAX_DELAY_S: Final[int] = 30
TELEMETRY_RETRY_BASE_DELAY_S: Final[int] = 1
