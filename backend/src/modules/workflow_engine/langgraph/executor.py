"""LangGraph Executor — invokes compiled graphs with thread isolation."""

import logging
from typing import Any

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

        try:
            result = await app.ainvoke(initial_state, config)
            return result
        except Exception as e:
            logger.error("Execution failed for graph %s: %s", graph_id, e)
            raise

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

        try:
            result = await app.ainvoke(resume_value, config)
            return result
        except Exception as e:
            logger.error("Resume failed for graph %s: %s", graph_id, e)
            raise
