"""PlatformOperationsService — public contract for the Operations module.

All external modules interact exclusively through this interface.
Operations module consumes execution events and exposes telemetry;
it never executes workflows, generates content, or modifies state.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID


class PlatformOperationsService(ABC):
    """Public interface for the Platform & Operations module."""

    @abstractmethod
    async def record_execution_start(
        self,
        workflow_id: str,
        workflow_type: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        """Record the start of a workflow execution.

        Creates the root LangSmith trace span, opens the OTel root span,
        and emits a structured JSON log for WORKFLOW_START event.

        Args:
            workflow_id: Unique workflow execution identifier.
            workflow_type: Category of workflow being executed.
            tags: Optional user-defined tags for searchability.
            metadata: Optional additional context.

        Returns:
            UUID of the created execution trace.

        Raises:
            OperationsError: If recording fails due to internal error
                (workflow execution continues unaffected).
        """

    @abstractmethod
    async def record_execution_complete(
        self,
        trace_id: UUID,
        workflow_id: str,
        status: str,
        duration_ms: int,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record the completion of a workflow execution.

        Finalizes the LangSmith trace, closes the OTel span, emits a
        structured JSON log, triggers guardrail evaluation, and updates
        operational metrics.

        Args:
            trace_id: Trace UUID from record_execution_start.
            workflow_id: Workflow execution identifier.
            status: Final status (completed, failed, cancelled).
            duration_ms: Total execution duration.
            error: Error message if the workflow failed.
            metadata: Optional additional context.
        """

    @abstractmethod
    async def record_ai_request(
        self,
        trace_id: UUID,
        workflow_id: str,
        prompt_version_id: UUID,
        prompt_name: str,
        model_name: str,
        model_version: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        status: str,
        error_message: str | None = None,
    ) -> UUID:
        """Record a single AI generation request.

        Creates a child LangSmith span, emits an OTel LLM span, logs a
        structured JSON entry, and updates token/cost records.

        Args:
            trace_id: Parent trace UUID.
            workflow_id: Workflow execution identifier.
            prompt_version_id: Immutable prompt version ID.
            prompt_name: Human-readable prompt name.
            model_name: Model identifier (e.g., 'gpt-4').
            model_version: Model version string.
            input_tokens: Number of prompt tokens.
            output_tokens: Number of generated tokens.
            latency_ms: Request latency.
            status: 'success' or 'error'.
            error_message: Error details if failed.

        Returns:
            UUID of the created telemetry record.

        Raises:
            OperationsError: If recording fails (workflow continues).
        """

    @abstractmethod
    def record_ai_request_sync(
        self,
        trace_id: UUID,
        workflow_id: str,
        prompt_version_id: UUID,
        prompt_name: str,
        model_name: str,
        model_version: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        status: str,
        error_message: str | None = None,
    ) -> UUID:
        """Synchronous form of record_ai_request.

        For callers running outside an event loop — notably the LangGraph
        agents' synchronous LLM service. Same semantics and arguments as
        record_ai_request.
        """

    @abstractmethod
    def register_or_get_prompt_version(
        self,
        name: str,
        template: str,
    ) -> UUID:
        """Return a stable prompt version ID for this name and template content.

        Registers the prompt on first sight and returns the existing ID on
        subsequent identical content, so telemetry from repeated runs of the
        same prompt correlates.

        Args:
            name: Human-readable prompt name.
            template: Resolved prompt template content.

        Returns:
            UUID version_id, stable for identical name + content.
        """

    @abstractmethod
    async def get_execution_history(
        self,
        workflow_id: str | None = None,
        status: str | None = None,
        time_range_start: datetime | None = None,
        time_range_end: datetime | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query searchable execution history.

        Args:
            workflow_id: Filter by workflow ID.
            status: Filter by status.
            time_range_start: Start of time range.
            time_range_end: End of time range.
            tags: Filter by tags (AND logic).
            limit: Maximum records to return (default 100, max 1000).
            offset: Pagination offset.

        Returns:
            List of execution history records.

        Raises:
            OperationsError: If query fails.
        """

    @abstractmethod
    async def get_metrics(
        self,
    ) -> dict[str, Any]:
        """Get current operational metrics.

        Returns:
            Dict with keys: latency_p50_ms, latency_p95_ms, latency_p99_ms,
            throughput, failure_rate, total_retries, total_cost_usd,
            total_tokens, window_start, window_end.
        """

    @abstractmethod
    async def register_prompt_version(
        self,
        name: str,
        template: str,
    ) -> UUID:
        """Register a new immutable prompt version.

        Args:
            name: Human-readable prompt name.
            template: Prompt template content.

        Returns:
            UUID version_id for the registered prompt.
        """

    @abstractmethod
    async def get_prompt_version(
        self,
        version_id: UUID,
    ) -> dict[str, Any] | None:
        """Look up a prompt version by its immutable ID.

        Args:
            version_id: Immutable prompt version UUID.

        Returns:
            Prompt version dict or None if not found.
        """

    @abstractmethod
    async def get_model_info(
        self,
        model_name: str,
        model_version: str | None = None,
    ) -> dict[str, Any] | None:
        """Get model metadata including cost and deprecation status.

        Args:
            model_name: Model identifier.
            model_version: Optional version filter.

        Returns:
            Model metadata dict or None if not found.
        """

    @abstractmethod
    async def export_executions(
        self,
        time_range_start: datetime,
        time_range_end: datetime,
        format: str = "jsonl",
    ) -> str:
        """Export execution history for offline evaluation.

        Args:
            time_range_start: Start of export range.
            time_range_end: End of export range.
            format: Export format (default 'jsonl').

        Returns:
            URL or path to the exported dataset.

        Raises:
            OperationsError: If export fails.
        """
