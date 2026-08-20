"""OpenTelemetry adapter for distributed tracing.

Configures TracerProvider, BatchSpanProcessor, and OTLP exporter.
Emits workflow, LLM, and tool spans with standard semantic conventions.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode


class OTelAdapter:
    """Adapter for OpenTelemetry span creation and management.

    Provides a thin wrapper around OTel Tracer that emits spans with
    semantic conventions for workflow, LLM, and tool execution layers.
    """

    def __init__(
        self,
        service_name: str = "ai-marketing-agent-operations",
        service_version: str = "0.1.0",
        environment: str = "development",
        otlp_endpoint: str | None = None,
    ) -> None:
        self._service_name = service_name
        self._tracer_provider: TracerProvider | None = None
        self._tracer: trace.Tracer | None = None
        self._configured = False

        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": service_version,
                "deployment.environment": environment,
            }
        )
        self._resource = resource

        if otlp_endpoint:
            self.configure(endpoint=otlp_endpoint)

    def configure(
        self,
        endpoint: str = "http://localhost:4318",
        headers: dict[str, str] | None = None,
        timeout_s: int = 10,
        max_queue_size: int = 2048,
        max_export_batch_size: int = 512,
    ) -> None:
        """Configure the OTel TracerProvider with OTLP export.

        Args:
            endpoint: OTLP HTTP exporter endpoint.
            headers: Optional HTTP headers for the exporter.
            timeout_s: Exporter timeout in seconds.
            max_queue_size: Maximum queue size for BatchSpanProcessor.
            max_export_batch_size: Maximum batch size for export.
        """
        provider = TracerProvider(resource=self._resource)
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            headers=headers or {},
            timeout=timeout_s,
        )
        processor = BatchSpanProcessor(
            exporter,
            max_queue_size=max_queue_size,
            max_export_batch_size=max_export_batch_size,
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        self._tracer_provider = provider
        self._tracer = trace.get_tracer(self._service_name)
        self._configured = True

    @property
    def is_configured(self) -> bool:
        return self._configured

    @property
    def tracer(self) -> trace.Tracer | None:
        return self._tracer

    @contextmanager
    def start_workflow_span(
        self,
        workflow_id: str,
        workflow_type: str,
    ) -> Generator[Span]:
        """Start a root span for a workflow execution.

        Args:
            workflow_id: Workflow execution identifier.
            workflow_type: Category of workflow.

        Yields:
            The OTel root span.
        """
        if not self._tracer:
            yield self._null_span()
            return

        attributes = {
            "workflow.id": workflow_id,
            "workflow.type": workflow_type,
            "workflow.status": "running",
        }

        with self._tracer.start_as_current_span(
            name=f"workflow.{workflow_type}",
            kind=trace.SpanKind.CONSUMER,
            attributes=attributes,
        ) as span:
            yield span

    @contextmanager
    def start_llm_span(
        self,
        model_name: str,
        model_version: str,
        prompt_version_id: str,
        max_tokens: int = 4096,
        parent_span: Span | None = None,
    ) -> Generator[Span]:
        """Start a child span for an LLM call.

        Args:
            model_name: Model identifier.
            model_version: Model version string.
            prompt_version_id: Immutable prompt version ID.
            max_tokens: Maximum tokens for generation.
            parent_span: Optional parent span for context.

        Yields:
            The OTel LLM span.
        """
        if not self._tracer:
            yield self._null_span()
            return

        attributes: dict[str, Any] = {
            "llm.model": model_name,
            "llm.model_version": model_version,
            "prompt.version": prompt_version_id,
            "gen_ai.request.max_tokens": max_tokens,
        }

        with self._tracer.start_as_current_span(
            name=f"llm.{model_name}",
            kind=trace.SpanKind.CLIENT,
            attributes=attributes,
        ) as span:
            yield span

    @contextmanager
    def start_tool_span(
        self,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
    ) -> Generator[Span]:
        """Start a child span for a tool invocation.

        Args:
            tool_name: Tool name.
            tool_input: Tool input data.

        Yields:
            The OTel tool span.
        """
        if not self._tracer:
            yield self._null_span()
            return

        attributes: dict[str, Any] = {
            "tool.name": tool_name,
        }
        if tool_input:
            attributes["tool.input"] = str(tool_input)

        with self._tracer.start_as_current_span(
            name=f"tool.{tool_name}",
            kind=trace.SpanKind.INTERNAL,
            attributes=attributes,
        ) as span:
            yield span

    def set_workflow_status(self, span: Span, status: str) -> None:
        """Set workflow status attribute on a span.

        Args:
            span: The OTel span to update.
            status: Workflow status value.
        """
        span.set_attribute("workflow.status", status)

    def set_llm_usage(
        self,
        span: Span,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Set token usage attributes on an LLM span.

        Args:
            span: The OTel LLM span to update.
            input_tokens: Input token count.
            output_tokens: Output token count.
        """
        span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", output_tokens)

    def set_tool_output(self, span: Span, output: str) -> None:
        """Set output attribute on a tool span.

        Args:
            span: The OTel tool span to update.
            output: Tool output string.
        """
        span.set_attribute("tool.output", output)

    def record_error(self, span: Span, error_message: str) -> None:
        """Record an error on a span.

        Args:
            span: The OTel span to mark as error.
            error_message: Error description.
        """
        span.set_status(Status(StatusCode.ERROR, error_message))
        span.record_exception(Exception(error_message))

    def _null_span(self) -> Span:
        """Return a no-op span when OTel is not configured."""
        return trace.NonRecordingSpan(
            trace.SpanContext(
                trace_id=0,
                span_id=0,
                is_remote=False,
            )
        )
