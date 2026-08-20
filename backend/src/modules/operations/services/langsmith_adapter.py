"""LangSmith adapter for AI workflow tracing.

Wraps langsmith.Client to provide workflow-level trace construction
with parent-child span hierarchies, error capture, and metadata injection.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from langsmith import Client as LangSmithClient
from langsmith.run_trees import RunTree

from ..constants import ExecutionStatus, SpanStatus, SpanType
from ..errors import TelemetryBackendError
from ..models.execution_trace import ExecutionTrace, TraceSpan
from ..services.telemetry_buffer import TelemetryBuffer


class LangSmithAdapter:
    """Adapter for LangSmith trace creation and management.

    Uses the RunTree API to construct parent-child span hierarchies
    representing workflow executions. All external calls are wrapped
    with TelemetryBuffer for resilience.
    """

    def __init__(
        self,
        project_name: str | None = None,
        buffer: TelemetryBuffer | None = None,
    ) -> None:
        self._project_name = project_name or "ai-marketing-agent"
        self._buffer = buffer
        self._client: LangSmithClient | None = None

    def _get_client(self) -> LangSmithClient:
        if self._client is None:
            try:
                self._client = LangSmithClient()
            except Exception as e:
                raise TelemetryBackendError(f"Failed to initialize LangSmith client: {e}") from e
        return self._client

    async def create_execution_trace(
        self,
        workflow_id: str,
        workflow_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionTrace:
        """Create a new execution trace with root LangSmith run.

        Args:
            workflow_id: Unique workflow execution identifier.
            workflow_type: Category of workflow.
            metadata: Optional additional context.

        Returns:
            ExecutionTrace with root span created.
        """
        trace = ExecutionTrace(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            metadata=metadata,
        )

        root_run = RunTree(
            name=f"workflow:{workflow_type}",
            run_type="chain",
            inputs={
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "metadata": metadata or {},
            },
            project_name=self._project_name,
        )

        root_span = TraceSpan(
            span_id=uuid4(),
            name=root_run.name,
            span_type=SpanType.WORKFLOW,
            start_time=datetime.now(UTC),
            input={"workflow_id": workflow_id, "workflow_type": workflow_type},
            metadata=metadata,
        )

        trace.root_span = root_span
        trace.add_span(root_span)
        trace._root_run = root_run

        await self._post_run(root_run)
        return trace

    async def create_child_span(
        self,
        trace: ExecutionTrace,
        name: str,
        span_type: SpanType,
        input_data: dict[str, Any] | None = None,
        parent_span_id: UUID | None = None,
    ) -> TraceSpan:
        """Create a child span within an execution trace.

        Args:
            trace: Parent execution trace.
            name: Span name.
            span_type: Category of span.
            input_data: Span input data.
            parent_span_id: Parent span ID. Uses root span if None.

        Returns:
            Created TraceSpan.
        """
        return self.build_child_span(
            trace=trace,
            name=name,
            span_type=span_type,
            input_data=input_data,
            parent_span_id=parent_span_id,
        )

    def build_child_span(
        self,
        trace: ExecutionTrace,
        name: str,
        span_type: SpanType,
        input_data: dict[str, Any] | None = None,
        parent_span_id: UUID | None = None,
    ) -> TraceSpan:
        """Synchronous child-span construction. Performs no I/O.

        Lets sync callers (e.g. the LangGraph agents' LLM service) attach
        spans without needing an event loop.
        """
        span = TraceSpan(
            span_id=uuid4(),
            parent_span_id=parent_span_id or trace.root_span.span_id if trace.root_span else None,
            name=name,
            span_type=span_type,
            start_time=datetime.now(UTC),
            input=input_data,
        )
        trace.add_span(span)
        return span

    async def end_span(
        self,
        span: TraceSpan,
        output: dict[str, Any] | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """End a trace span with output, error, and metadata.

        Args:
            span: The span to end.
            output: Span output data.
            error: Error message if the span failed.
            metadata: Additional metadata to attach.
        """
        now = datetime.now(UTC)
        span.end_time = now
        if span.start_time:
            span.duration_ms = int((now - span.start_time).total_seconds() * 1000)
        span.output = output
        span.error = error
        span.status = SpanStatus.ERROR if error else SpanStatus.SUCCESS
        if metadata:
            if span.metadata:
                span.metadata.update(metadata)
            else:
                span.metadata = metadata

    async def finalize_trace(
        self,
        trace: ExecutionTrace,
        status: str,
        error: str | None = None,
    ) -> None:
        """Finalize an execution trace.

        Ends the root span and posts the complete trace to LangSmith.

        Args:
            trace: Execution trace to finalize.
            status: Final execution status.
            error: Error message if failed.
        """
        if trace.root_span:
            trace.root_span.end_time = datetime.now(UTC)
            if trace.root_span.start_time:
                trace.root_span.duration_ms = int(
                    (trace.root_span.end_time - trace.root_span.start_time).total_seconds() * 1000
                )

        trace.status = ExecutionStatus(status) if isinstance(status, str) else status
        if error:
            trace.error = error

        root_run = getattr(trace, "_root_run", None)
        if root_run is not None:
            root_run.end(outputs=trace.to_dict(), error=error)
            await self._post_run(root_run, patch=True)

    async def _post_run(self, run: RunTree, patch: bool = False) -> None:
        """Post (or patch) a RunTree to LangSmith, optionally through the buffer.

        Args:
            run: RunTree to send.
            patch: Send as an update to an already-posted run.
        """
        if self._buffer is not None:
            await self._buffer.enqueue(("patch_run" if patch else "post_run", run))
        else:
            try:
                run.patch() if patch else run.post()
            except Exception as e:
                raise TelemetryBackendError(f"Failed to post LangSmith run: {e}") from e

    def _inject_ai_metadata(
        self,
        span: TraceSpan,
        prompt_version_id: UUID,
        prompt_name: str,
        model_name: str,
        model_version: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        estimated_cost_usd: float,
    ) -> None:
        """Inject AI request metadata into a span.

        Args:
            span: The span to attach metadata to.
            prompt_version_id: Immutable prompt version ID.
            prompt_name: Human-readable prompt name.
            model_name: Model identifier.
            model_version: Model version string.
            input_tokens: Input token count.
            output_tokens: Output token count.
            total_tokens: Total token count.
            estimated_cost_usd: Estimated cost in USD.
        """
        metadata = {
            "prompt_version_id": str(prompt_version_id),
            "prompt_name": prompt_name,
            "model_name": model_name,
            "model_version": model_version,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost_usd,
        }
        if span.metadata:
            span.metadata.update(metadata)
        else:
            span.metadata = metadata
