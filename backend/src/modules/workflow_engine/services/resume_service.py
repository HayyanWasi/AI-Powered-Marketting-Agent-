"""Resume Service — resumes workflow execution from last checkpoint."""

import logging

from ..models import WorkflowContext, ExecutionState

logger = logging.getLogger(__name__)


class ResumeService:
    """Manages workflow resume from checkpoints."""

    def __init__(self):
        self._checkpoints: dict[str, WorkflowContext] = {}

    def save_checkpoint(self, thread_id: str, context: WorkflowContext) -> None:
        self._checkpoints[thread_id] = context
        logger.debug("Checkpoint saved for thread %s at node %s", thread_id, context.current_node)

    def get_checkpoint(self, thread_id: str) -> WorkflowContext | None:
        return self._checkpoints.get(thread_id)

    def has_checkpoint(self, thread_id: str) -> bool:
        return thread_id in self._checkpoints

    def resume(self, thread_id: str) -> WorkflowContext:
        context = self._checkpoints.get(thread_id)
        if not context:
            raise ValueError(f"No checkpoint found for thread {thread_id}")

        logger.info(
            "Resuming thread %s from node %s",
            thread_id,
            context.current_node,
        )

        return context.with_updates(state=ExecutionState.RUNNING)

    def clear_checkpoint(self, thread_id: str) -> None:
        self._checkpoints.pop(thread_id, None)
