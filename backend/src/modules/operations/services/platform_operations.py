"""PlatformOperationsService — concrete implementation.

Wires all internal services together behind the public
PlatformOperationsService ABC. This is the single entry point for all
external modules consuming operations telemetry.
"""

import logging
from contextlib import ExitStack
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.utils.sanitizer import sanitize_error_message

from ..constants import ExecutionStatus, SpanType
from ..interfaces.operations import PlatformOperationsService as PlatformOperationsServiceABC
from ..models.execution_history import ExecutionHistoryRecord
from ..models.execution_trace import ExecutionTrace
from ..repositories.execution_history_repository import ExecutionHistoryRepository
from ..services.cost_tracker import CostTracker
from ..services.export_service import ExportService
from ..services.guardrail_engine import GuardrailEngine
from ..services.json_logger import JSONLogger
from ..services.langsmith_adapter import LangSmithAdapter
from ..services.metrics_collector import MetricsCollector
from ..services.model_pricing import seed_model_registry
from ..services.model_registry import ModelVersionRegistry
from ..services.otel_adapter import OTelAdapter
from ..services.prompt_registry import PromptVersionRegistry
from ..services.telemetry_buffer import TelemetryBuffer

logger = logging.getLogger(__name__)


class PlatformOperationsService(PlatformOperationsServiceABC):
    """Concrete implementation of the PlatformOperationsService.

    Composes all internal observability services and exposes them through
    the public ABC interface. All external calls are resilient — failures
    in telemetry backends never interrupt workflow execution.
    """

    def __init__(
        self,
        project_name: str = "ai-marketing-agent",
        service_name: str = "ai-marketing-agent-operations",
        otlp_endpoint: str | None = None,
        supabase_client: Any | None = None,
        langsmith_buffer_maxsize: int = 10000,
        otel_buffer_maxsize: int = 10000,
        log_buffer_maxsize: int = 10000,
    ) -> None:
        # Registries
        self.prompt_registry = PromptVersionRegistry()
        self.model_registry = ModelVersionRegistry()
        seed_model_registry(self.model_registry)

        # Telemetry buffers
        self._langsmith_buffer = TelemetryBuffer(
            name="langsmith",
            maxsize=langsmith_buffer_maxsize,
            flush_fn=self._flush_langsmith_item,
        )
        self._otel_buffer = TelemetryBuffer(name="otel", maxsize=otel_buffer_maxsize)
        self._log_buffer = TelemetryBuffer(name="logger", maxsize=log_buffer_maxsize)

        # Core services
        self.json_logger = JSONLogger()
        self.langsmith = LangSmithAdapter(
            project_name=project_name,
            buffer=self._langsmith_buffer,
        )
        self.otel = OTelAdapter(
            service_name=service_name,
            otlp_endpoint=otlp_endpoint,
        )
        self.cost_tracker = CostTracker()
        self.metrics_collector = MetricsCollector()
        self.guardrail_engine = GuardrailEngine()

        # History persistence
        self._history_repo = ExecutionHistoryRepository(supabase=supabase_client)
        self.export_service = ExportService(repository=self._history_repo)

        # Active traces
        self._active_traces: dict[UUID, ExecutionTrace] = {}
        self._trace_start_times: dict[UUID, datetime] = {}
        self._workflow_spans: dict[UUID, tuple[ExitStack, Any]] = {}
        self._trace_user_ids: dict[UUID, str | UUID | None] = {}

    async def initialize(self) -> None:
        """Start background flush tasks for all telemetry buffers."""
        await self._langsmith_buffer.start_auto_flush(interval_s=5.0)
        await self._otel_buffer.start_auto_flush(interval_s=5.0)
        await self._log_buffer.start_auto_flush(interval_s=5.0)

    async def shutdown(self) -> None:
        """Stop background tasks and flush remaining data."""
        await self._langsmith_buffer.flush()
        await self._otel_buffer.flush()
        await self._log_buffer.flush()
        await self._langsmith_buffer.stop_auto_flush()
        await self._otel_buffer.stop_auto_flush()
        await self._log_buffer.stop_auto_flush()

    async def _flush_langsmith_item(self, item: Any) -> bool:
        """Flush a LangSmith buffer item by posting or patching its RunTree."""
        try:
            if isinstance(item, tuple) and item[0] in ("post_run", "patch_run"):
                if item[0] == "patch_run":
                    item[1].patch()
                else:
                    item[1].post()
                return True
            return False
        except Exception as e:
            logger.warning("LangSmith flush failed: %s", e)
            return False

    async def record_execution_start(
        self,
        workflow_id: str,
        workflow_type: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: str | UUID | None = None,
    ) -> UUID:
        """Record the start of a workflow execution.

        Creates LangSmith trace, opens OTel span, emits JSON log,
        and records pending execution history entry.
        """
        resolved_user_id = user_id or (metadata.get("user_id") if metadata else None)

        try:
            trace = await self.langsmith.create_execution_trace(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                metadata=metadata,
            )
        except Exception as e:
            logger.warning("LangSmith trace creation failed for %s: %s", workflow_id, e)
            trace = ExecutionTrace(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                metadata=metadata,
            )

        trace.user_id = resolved_user_id
        self._active_traces[trace.id] = trace
        self._trace_start_times[trace.id] = datetime.now(UTC)
        self._trace_user_ids[trace.id] = resolved_user_id

        try:
            stack = ExitStack()
            span = stack.enter_context(
                self.otel.start_workflow_span(workflow_id=workflow_id, workflow_type=workflow_type)
            )
            self._workflow_spans[trace.id] = (stack, span)
        except Exception as e:
            logger.warning("OTel workflow span failed for %s: %s", workflow_id, e)

        self.json_logger.workflow_start(
            workflow_id=workflow_id,
            trace_id=str(trace.id),
            metadata={"workflow_type": workflow_type, "tags": tags},
        )

        return trace.id

    async def record_execution_complete(
        self,
        trace_id: UUID,
        workflow_id: str,
        status: str,
        duration_ms: int,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: str | UUID | None = None,
    ) -> None:
        """Record workflow completion with guardrails, metrics, and history."""
        trace = self._active_traces.pop(trace_id, None)
        start_time = self._trace_start_times.pop(trace_id, None)
        span_entry = self._workflow_spans.pop(trace_id, None)
        stored_user_id = self._trace_user_ids.pop(trace_id, None)
        if not trace:
            return

        sanitized_error = sanitize_error_message(error)
        resolved_user_id = (
            user_id
            or getattr(trace, "user_id", None)
            or stored_user_id
            or (metadata.get("user_id") if metadata else None)
            or (trace.metadata.get("user_id") if trace and trace.metadata else None)
        )

        if span_entry is not None:
            stack, span = span_entry
            try:
                self.otel.set_workflow_status(span, status)
                if sanitized_error:
                    self.otel.record_error(span, sanitized_error)
            except Exception as e:
                logger.warning("OTel workflow span update failed for %s: %s", workflow_id, e)
            finally:
                stack.close()

        try:
            await self.langsmith.finalize_trace(
                trace=trace,
                status=status,
                error=sanitized_error,
            )
        except Exception as e:
            logger.warning("LangSmith trace finalization failed for %s: %s", workflow_id, e)

        # Emit JSON log
        if sanitized_error:
            self.json_logger.workflow_fail(
                workflow_id=workflow_id,
                duration_ms=duration_ms,
                error=sanitized_error,
                trace_id=str(trace_id),
                metadata=metadata,
            )
        else:
            self.json_logger.workflow_complete(
                workflow_id=workflow_id,
                duration_ms=duration_ms,
                trace_id=str(trace_id),
                metadata=metadata,
            )

        # Run guardrails
        cost_data = self.cost_tracker.get_workflow_cost(workflow_id)
        guardrail_results = self.guardrail_engine.evaluate(
            workflow_id=workflow_id,
            actual_values={
                "total_cost_usd": cost_data["total_cost_usd"],
                "latency_ms": duration_ms,
                "total_tokens": cost_data["total_tokens"],
                "model_version": (metadata or {}).get("model_version", ""),
            },
            deprecated_models=self._deprecated_model_versions(),
        )

        for gr in guardrail_results:
            self.json_logger.guardrail_evaluation(
                workflow_id=workflow_id,
                rule_name=gr.rule_name,
                passed=gr.passed,
                actual_value=gr.actual_value,
                threshold=gr.threshold_value,
                severity=gr.rule_severity.value,
            )

        # Update metrics
        self.metrics_collector.record_execution(
            duration_ms=duration_ms,
            status=status,
            total_cost_usd=cost_data["total_cost_usd"],
            total_tokens=cost_data["total_tokens"],
        )

        # Persist execution history
        end_time = datetime.now(UTC)
        history_record = ExecutionHistoryRecord(
            user_id=resolved_user_id,
            workflow_id=workflow_id,
            workflow_type=trace.workflow_type,
            status=ExecutionStatus(status),
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            total_cost_usd=cost_data["total_cost_usd"],
            total_tokens=cost_data["total_tokens"],
            metadata=metadata,
            trace_id=trace_id,
            guardrail_summary={
                "total": len(guardrail_results),
                "violations": sum(1 for g in guardrail_results if not g.passed),
            },
        )

        try:
            await self._history_repo.insert(history_record)
        except Exception as e:
            logger.warning("Execution history persistence failed for %s: %s", workflow_id, e)

        # Clean up cost tracker
        self.cost_tracker.clear_workflow(workflow_id)

    def _deprecated_model_versions(self) -> list[str]:
        """Collect deprecated model version strings from the registry."""
        deprecated: list[str] = []
        for model_name in self.model_registry.list_models():
            for version in self.model_registry.list_versions(model_name):
                if version["is_deprecated"]:
                    deprecated.append(version["model_version"])
        return deprecated

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
        """Record an AI request with cost tracking and telemetry emission."""
        return self._record_ai_request_core(
            trace_id=trace_id,
            workflow_id=workflow_id,
            prompt_version_id=prompt_version_id,
            prompt_name=prompt_name,
            model_name=model_name,
            model_version=model_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )

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
        """Synchronous variant for callers without a running event loop."""
        return self._record_ai_request_core(
            trace_id=trace_id,
            workflow_id=workflow_id,
            prompt_version_id=prompt_version_id,
            prompt_name=prompt_name,
            model_name=model_name,
            model_version=model_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )

    def _record_ai_request_core(
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
        """Shared implementation for the sync and async record_ai_request paths."""
        # Look up model pricing
        model_info = self.model_registry.get(model_name, model_version)
        if not model_info:
            logger.warning(
                "No registry entry for %s/%s — cost will be recorded as zero",
                model_name,
                model_version,
            )
        cost_per_input = model_info["cost_per_input_token"] if model_info else 0.0
        cost_per_output = model_info["cost_per_output_token"] if model_info else 0.0

        # Record cost
        telemetry = self.cost_tracker.record_ai_call(
            workflow_id=workflow_id,
            prompt_version_id=prompt_version_id,
            prompt_name=prompt_name,
            model_name=model_name,
            model_version=model_version,
            provider=model_info["provider"] if model_info else "unknown",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_per_input_token=cost_per_input,
            cost_per_output_token=cost_per_output,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )

        # Update LangSmith trace if active
        trace = self._active_traces.get(trace_id)
        if trace:
            try:
                span = self.langsmith.build_child_span(
                    trace=trace,
                    name=f"ai.{model_name}",
                    span_type=SpanType.LLM,
                    input_data={
                        "prompt_version_id": str(prompt_version_id),
                        "model_name": model_name,
                        "model_version": model_version,
                    },
                )
                self.langsmith._inject_ai_metadata(
                    span=span,
                    prompt_version_id=prompt_version_id,
                    prompt_name=prompt_name,
                    model_name=model_name,
                    model_version=model_version,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=telemetry.total_tokens,
                    estimated_cost_usd=telemetry.estimated_cost_usd,
                )
            except Exception as e:
                logger.warning("LangSmith LLM span failed for %s: %s", workflow_id, e)

        # OTel LLM span
        try:
            with self.otel.start_llm_span(
                model_name=model_name,
                model_version=model_version,
                prompt_version_id=str(prompt_version_id),
            ) as llm_span:
                self.otel.set_llm_usage(
                    span=llm_span,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                if error_message:
                    self.otel.record_error(llm_span, error_message)
        except Exception as e:
            logger.warning("OTel LLM span failed for %s: %s", workflow_id, e)

        # JSON log
        self.json_logger.ai_request(
            workflow_id=workflow_id,
            model_name=model_name,
            model_version=model_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            prompt_version_id=str(prompt_version_id),
            estimated_cost_usd=telemetry.estimated_cost_usd,
            status=status,
            error_message=error_message,
        )

        return telemetry.id

    async def get_execution_history(
        self,
        user_id: str | UUID | None = None,
        workflow_id: str | None = None,
        status: str | None = None,
        time_range_start: datetime | None = None,
        time_range_end: datetime | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query execution history with filters and pagination."""
        return await self._history_repo.query(
            user_id=user_id,
            workflow_id=workflow_id,
            status=status,
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    async def get_metrics(self) -> dict[str, Any]:
        """Get current operational metrics snapshot."""
        return self.metrics_collector.get_snapshot().to_dict()

    async def register_prompt_version(
        self,
        name: str,
        template: str,
    ) -> UUID:
        """Register an immutable prompt version."""
        return self.prompt_registry.register(name, template)

    def register_or_get_prompt_version(self, name: str, template: str) -> UUID:
        """Return a stable version id for this prompt name + content."""
        return self.prompt_registry.register_or_get(name, template)

    async def get_prompt_version(
        self,
        version_id: UUID,
    ) -> dict[str, Any] | None:
        """Look up a prompt version by immutable ID."""
        return self.prompt_registry.get(version_id)

    async def get_model_info(
        self,
        model_name: str,
        model_version: str | None = None,
    ) -> dict[str, Any] | None:
        """Get model metadata including cost and deprecation status."""
        return self.model_registry.get(model_name, model_version)

    async def export_executions(
        self,
        time_range_start: datetime,
        time_range_end: datetime,
        format: str = "jsonl",
    ) -> str:
        """Export execution history for offline evaluation."""
        return await self.export_service.export(
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            format=format,
        )
