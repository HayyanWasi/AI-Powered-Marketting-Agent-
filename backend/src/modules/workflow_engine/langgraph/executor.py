"""LangGraph Executor — invokes compiled graphs with thread isolation."""

import logging
import time
from typing import Any

from src.api.dependencies import get_operations_service
from src.modules.operations.constants import ExecutionStatus
from src.modules.operations.context import reset_execution_context, set_execution_context

logger = logging.getLogger(__name__)


class LangGraphExecutor:
    """Executes compiled LangGraph apps with thread isolation."""

    def __init__(self):
        self._compiled_apps: dict[str, Any] = {}

    def register(self, graph_id: str, compiled_app: Any) -> None:
        self._compiled_apps[graph_id] = compiled_app

    async def execute(
        self,
        graph_id: str,
        initial_state: dict,
        thread_id: str,
    ) -> Any:
        app = self._compiled_apps.get(graph_id)
        if not app:
            raise ValueError(f"No compiled graph found for {graph_id}")

        config = {"configurable": {"thread_id": thread_id}}
        operations = get_operations_service()

        trace_id = await operations.record_execution_start(
            workflow_id=thread_id, workflow_type=graph_id, metadata={"initial_state": True}
        )

        start_time = time.perf_counter()
        token = set_execution_context(trace_id=trace_id, workflow_id=thread_id)
        try:
            result = await app.ainvoke(initial_state, config)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            await operations.record_execution_complete(
                trace_id=trace_id,
                workflow_id=thread_id,
                status=ExecutionStatus.COMPLETED.value,
                duration_ms=duration_ms,
            )
            return result
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            await operations.record_execution_complete(
                trace_id=trace_id,
                workflow_id=thread_id,
                status=ExecutionStatus.FAILED.value,
                duration_ms=duration_ms,
                error=str(e),
            )
            logger.error("Execution failed for graph %s: %s", graph_id, e)
            raise
        finally:
            reset_execution_context(token)

    async def resume(
        self,
        graph_id: str,
        thread_id: str,
        resume_value: Any = None,
    ) -> Any:
        app = self._compiled_apps.get(graph_id)
        if not app:
            raise ValueError(f"No compiled graph found for {graph_id}")

        config = {"configurable": {"thread_id": thread_id}}
        operations = get_operations_service()

        trace_id = await operations.record_execution_start(
            workflow_id=thread_id,
            workflow_type=graph_id,
            metadata={"resume_value": str(resume_value)[:100]},
        )

        start_time = time.perf_counter()
        token = set_execution_context(trace_id=trace_id, workflow_id=thread_id)
        try:
            result = await app.ainvoke(resume_value, config)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            await operations.record_execution_complete(
                trace_id=trace_id,
                workflow_id=thread_id,
                status=ExecutionStatus.COMPLETED.value,
                duration_ms=duration_ms,
            )
            return result
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            await operations.record_execution_complete(
                trace_id=trace_id,
                workflow_id=thread_id,
                status=ExecutionStatus.FAILED.value,
                duration_ms=duration_ms,
                error=str(e),
            )
            logger.error("Resume failed for graph %s: %s", graph_id, e)
            raise
        finally:
            reset_execution_context(token)
