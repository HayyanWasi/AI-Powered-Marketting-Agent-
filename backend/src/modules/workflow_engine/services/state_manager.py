"""State Manager — manages workflow execution state transitions."""

import logging
from typing import Any

from ..models import ExecutionState, WorkflowContext

logger = logging.getLogger(__name__)


class StateManager:
    """Manages workflow state transitions and node output tracking."""

    def __init__(self):
        self._completed_nodes: dict[str, list[str]] = {}
        self._node_outputs: dict[str, dict[str, Any]] = {}

    def initialize(self, thread_id: str, context: WorkflowContext) -> WorkflowContext:
        self._completed_nodes[thread_id] = []
        self._node_outputs[thread_id] = {}
        return context.with_updates(state=ExecutionState.RUNNING)

    def mark_node_completed(self, thread_id: str, node_name: str, output: Any) -> None:
        if thread_id not in self._completed_nodes:
            self._completed_nodes[thread_id] = []
        if node_name not in self._completed_nodes[thread_id]:
            self._completed_nodes[thread_id].append(node_name)

        if thread_id not in self._node_outputs:
            self._node_outputs[thread_id] = {}
        self._node_outputs[thread_id][node_name] = output

        logger.debug("Node %s completed for thread %s", node_name, thread_id)

    def mark_node_failed(self, thread_id: str, node_name: str, error: Exception) -> None:
        logger.warning("Node %s failed for thread %s: %s", node_name, thread_id, error)

    def get_completed_nodes(self, thread_id: str) -> list[str]:
        return self._completed_nodes.get(thread_id, [])

    def get_node_output(self, thread_id: str, node_name: str) -> Any | None:
        return self._node_outputs.get(thread_id, {}).get(node_name)

    def get_all_outputs(self, thread_id: str) -> dict[str, Any]:
        return self._node_outputs.get(thread_id, {})

    def is_node_completed(self, thread_id: str, node_name: str) -> bool:
        return node_name in self._completed_nodes.get(thread_id, [])

    def get_next_node(
        self,
        graph: Any,
        current_node: str,
        context: WorkflowContext,
    ) -> str | None:
        for edge in graph.edges:
            if edge["source"] == current_node:
                if not self.is_node_completed(context.thread_id, edge["target"]):
                    return edge["target"]

        for edge in graph.conditional_edges:
            if edge["source"] == current_node:
                condition = edge.get("condition")
                if condition and condition(context):
                    return edge["target"]

        return None

    def restore_checkpoint(self, thread_id: str, context: WorkflowContext) -> WorkflowContext:
        completed = self.get_completed_nodes(thread_id)
        logger.info(
            "Restoring thread %s with %d completed nodes",
            thread_id,
            len(completed),
        )
        return context.with_updates(state=ExecutionState.RUNNING)

    def clear(self, thread_id: str) -> None:
        self._completed_nodes.pop(thread_id, None)
        self._node_outputs.pop(thread_id, None)
