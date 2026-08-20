"""Structured JSON logging service."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from ..constants import TelemetryEventType


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs log records as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "workflow_id"):
            log_entry["workflow_id"] = record.workflow_id
        if hasattr(record, "event_type"):
            log_entry["event_type"] = record.event_type
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id
        if hasattr(record, "metadata"):
            log_entry["metadata"] = record.metadata
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


class JSONLogger:
    """Operational event logger that emits structured JSON.

    Provides convenience methods for logging operational events with
    consistent structure across workflow, AI, guardrail, and buffer events.
    """

    def __init__(self, name: str = "operations", level: int = logging.INFO) -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._logger.handlers.clear()

        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self._logger.addHandler(handler)
        self._logger.propagate = False

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def _log(
        self,
        level: int,
        event_type: TelemetryEventType,
        message: str,
        workflow_id: str | None = None,
        duration_ms: int | None = None,
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        extra: dict[str, Any] = {
            "event_type": event_type.value,
        }
        if workflow_id:
            extra["workflow_id"] = workflow_id
        if duration_ms is not None:
            extra["duration_ms"] = duration_ms
        if trace_id:
            extra["trace_id"] = trace_id
        if metadata:
            extra["metadata"] = metadata
        self._logger.log(level, message, extra=extra)

    def workflow_start(
        self,
        workflow_id: str,
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._log(
            logging.INFO,
            TelemetryEventType.WORKFLOW_START,
            f"Workflow started: {workflow_id}",
            workflow_id=workflow_id,
            trace_id=trace_id,
            metadata=metadata,
        )

    def workflow_complete(
        self,
        workflow_id: str,
        duration_ms: int,
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._log(
            logging.INFO,
            TelemetryEventType.WORKFLOW_COMPLETE,
            f"Workflow completed: {workflow_id}",
            workflow_id=workflow_id,
            duration_ms=duration_ms,
            trace_id=trace_id,
            metadata=metadata,
        )

    def workflow_fail(
        self,
        workflow_id: str,
        duration_ms: int,
        error: str,
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        merged = dict(metadata or {})
        merged["error"] = error
        self._log(
            logging.ERROR,
            TelemetryEventType.WORKFLOW_FAIL,
            f"Workflow failed: {workflow_id} - {error}",
            workflow_id=workflow_id,
            duration_ms=duration_ms,
            trace_id=trace_id,
            metadata=merged,
        )

    def workflow_retry(
        self,
        workflow_id: str,
        attempt: int,
        error: str,
        trace_id: str | None = None,
    ) -> None:
        self._log(
            logging.WARNING,
            TelemetryEventType.WORKFLOW_RETRY,
            f"Workflow retry {attempt}: {workflow_id} - {error}",
            workflow_id=workflow_id,
            trace_id=trace_id,
            metadata={"attempt": attempt, "error": error},
        )

    def ai_request(
        self,
        workflow_id: str,
        model_name: str,
        model_version: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        prompt_version_id: str | None = None,
        estimated_cost_usd: float | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> None:
        metadata: dict[str, Any] = {
            "model_name": model_name,
            "model_version": model_version,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "latency_ms": latency_ms,
            "status": status,
        }
        if prompt_version_id:
            metadata["prompt_version_id"] = prompt_version_id
        if estimated_cost_usd is not None:
            metadata["execution_cost_usd"] = estimated_cost_usd
        if error_message:
            metadata["error_message"] = error_message
        self._log(
            logging.INFO,
            TelemetryEventType.AI_REQUEST_COMPLETE,
            f"AI request: {model_name}/{model_version} - {status}",
            workflow_id=workflow_id,
            metadata=metadata,
        )

    def guardrail_evaluation(
        self,
        workflow_id: str,
        rule_name: str,
        passed: bool,
        actual_value: float,
        threshold: float,
        severity: str,
    ) -> None:
        self._log(
            logging.WARNING if not passed else logging.INFO,
            TelemetryEventType.GUARDRAIL_EVALUATION,
            f"Guardrail '{rule_name}': {'PASS' if passed else 'FAIL'} "
            f"(actual={actual_value}, threshold={threshold})",
            workflow_id=workflow_id,
            metadata={
                "rule_name": rule_name,
                "passed": passed,
                "actual_value": actual_value,
                "threshold": threshold,
                "severity": severity,
            },
        )

    def buffer_status(
        self,
        event: str,
        fill_pct: float,
        dropped: int = 0,
        retry_count: int = 0,
    ) -> None:
        self._log(
            logging.WARNING if fill_pct > 80 else logging.INFO,
            TelemetryEventType.TELEMETRY_BUFFER_STATUS,
            f"Buffer {event}: {fill_pct:.1f}% full",
            metadata={
                "event": event,
                "fill_percentage": fill_pct,
                "dropped": dropped,
                "retry_count": retry_count,
            },
        )
