"""Custom exceptions for the Platform & Operations module."""


class OperationsError(Exception):
    """Base exception for all Operations module errors."""


class TelemetryBackendError(OperationsError):
    """Raised when a telemetry backend (LangSmith, OTel, log aggregator)
    is unreachable or returns an error. Workflow execution continues
    unaffected — this error is caught by the telemetry buffer."""


class GuardrailEvaluationError(OperationsError):
    """Raised when a guardrail rule evaluation itself fails.
    The workflow continues and the evaluation failure is logged."""


class BufferOverflowError(OperationsError):
    """Raised when a telemetry buffer reaches capacity and drops the
    oldest item. This is informational — the drop is handled gracefully."""


class RegistryError(OperationsError):
    """Raised when a prompt or model registry operation fails
    (e.g., duplicate registration, lookup miss)."""


class HistoryQueryError(OperationsError):
    """Raised when an execution history query fails."""


class ExportError(OperationsError):
    """Raised when an offline evaluation export fails."""
