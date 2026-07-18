"""Checkpoint Service - Manages workflow checkpoints."""

from typing import Dict, Any, List, Optional
from datetime import datetime

from .models.execution_checkpoint import ExecutionCheckpoint
from .models.workflow_context import WorkflowContext
from .models.execution_state import ExecutionState


class CheckpointService:
    """Service that manages workflow checkpoints.

    The CheckpointService is responsible for creating, storing, retrieving,
    and managing workflow execution checkpoints. Checkpoints allow workflows
    to be interrupted and resumed from the last successful completion point
    without re-executing completed nodes.

    Each checkpoint stores:
    - Current node
    - Workflow state
    - Node outputs
    - Execution progress

    The service supports checkpoint creation after successful node execution
    and resume operations from the latest checkpoint.
    """

    def __init__(self):
        # In-memory checkpoint storage
        self._checkpoints: Dict[str, ExecutionCheckpoint] = {}
        self._workflow_state: Dict[str, WorkflowContext] = {}
        self._checkpoint_counter = 0

    def create_checkpoint(
        self, thread_id: str, node_name: str, workflow_context: WorkflowContext
    ) -> ExecutionCheckpoint:
        """Create a new checkpoint after successful node execution.

        Args:
            thread_id: Workflow thread ID
            node_name: Name of the last successfully completed node
            workflow_context: Current workflow context

        Returns:
            Created ExecutionCheckpoint

        Raises:
            ValueError: If thread_id or node_name is empty
        """
        if not thread_id:
            raise ValueError("thread_id cannot be empty")
        if not node_name:
            raise ValueError("node_name cannot be empty")

        self._checkpoint_counter += 1
        checkpoint_id = f"checkpoint-{self._checkpoint_counter}"

        checkpoint = ExecutionCheckpoint(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            node_name=node_name,
        )

        self._checkpoints[checkpoint_id] = checkpoint
        self._workflow_state[thread_id] = workflow_context

        return checkpoint

    def get_latest_checkpoint(self, thread_id: str) -> Optional[ExecutionCheckpoint]:
        """Get the latest checkpoint for a workflow.

        Args:
            thread_id: Workflow thread ID

        Returns:
            Latest ExecutionCheckpoint or None if not found
        """
        checkpoints = [cp for cp in self._checkpoints.values() if cp.thread_id == thread_id]

        if not checkpoints:
            return None

        return max(checkpoints, key=lambda x: x.timestamp)

    def get_checkpoint(self, checkpoint_id: str) -> Optional[ExecutionCheckpoint]:
        """Get a specific checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            ExecutionCheckpoint or None if not found
        """
        return self._checkpoints.get(checkpoint_id)

    def restore_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Restore workflow state from the latest checkpoint.

        Args:
            thread_id: Workflow thread ID

        Returns:
            Workflow context dictionary or None if no checkpoint exists
        """
        if thread_id not in self._workflow_state:
            return None

        return self._workflow_state[thread_id].to_dict()

    def list_checkpoints(
        self, thread_id: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List available checkpoints.

        Args:
            thread_id: Optional filter by thread ID
            limit: Maximum number of checkpoints to return

        Returns:
            List of checkpoint metadata
        """
        checkpoints = list(self._checkpoints.values())

        if thread_id:
            checkpoints = [cp for cp in checkpoints if cp.thread_id == thread_id]

        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply limit
        checkpoints = checkpoints[:limit]

        return [
            {
                "checkpoint_id": cp.checkpoint_id,
                "thread_id": cp.thread_id,
                "timestamp": cp.timestamp.isoformat(),
                "node_name": cp.node_name,
            }
            for cp in checkpoints
        ]

    def remove_checkpoint(self, checkpoint_id: str) -> bool:
        """Remove a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to remove

        Returns:
            True if checkpoint was removed, False if not found
        """
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            return True
        return False

    def cleanup_expired_checkpoints(
        self, older_than_hours: int, thread_id: Optional[str] = None
    ) -> int:
        """Remove expired checkpoints.

        Args:
            older_than_hours: Age threshold for cleanup
            thread_id: Optional filter by thread ID

        Returns:
            Number of checkpoints removed
        """
        cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
        expired_checkpoint_ids = []

        for checkpoint_id, checkpoint in self._checkpoints.items():
            if checkpoint.timestamp.timestamp() < cutoff_time:
                if thread_id is None or checkpoint.thread_id == thread_id:
                    expired_checkpoint_ids.append(checkpoint_id)

        for checkpoint_id in expired_checkpoint_ids:
            del self._checkpoints[checkpoint_id]
            if checkpoint_id in self._workflow_state:
                thread_id_to_remove = self._workflow_state[checkpoint_id].thread_id
                del self._workflow_state[thread_id_to_remove]

        return len(expired_checkpoint_ids)

    def get_all_checkpoints_for_workflow(self, thread_id: str) -> List[ExecutionCheckpoint]:
        """Get all checkpoints for a workflow.

        Args:
            thread_id: Workflow thread ID

        Returns:
            List of all checkpoints for the workflow, sorted by timestamp
        """
        return [cp for cp in self._checkpoints.values() if cp.thread_id == thread_id]

    def update_checkpoint(
        self, thread_id: str, node_name: str, workflow_context: WorkflowContext
    ) -> Optional[ExecutionCheckpoint]:
        """Update an existing checkpoint.

        Args:
            thread_id: Workflow thread ID
            node_name: Name of the completed node
            workflow_context: Current workflow context

        Returns:
            Updated checkpoint or None if thread_id not found
        """
        if thread_id not in self._workflow_state:
            return None

        # Get latest checkpoint for this thread
        latest_checkpoint = self.get_latest_checkpoint(thread_id)
        if not latest_checkpoint:
            return None

        # Update checkpoint with new completion
        updated_checkpoint = ExecutionCheckpoint(
            thread_id=thread_id,
            checkpoint_id=latest_checkpoint.checkpoint_id,
            timestamp=datetime.now(),
            node_name=node_name,
        )

        self._checkpoints[latest_checkpoint.checkpoint_id] = updated_checkpoint
        self._workflow_state[thread_id] = workflow_context

        return updated_checkpoint

    def validate_checkpoint_integrity(self, thread_id: str) -> Dict[str, Any]:
        """Validate checkpoint integrity.

        Args:
            thread_id: Workflow thread ID

        Returns:
            Dict containing validation results
        """
        checkpoints = self.get_all_checkpoints_for_workflow(thread_id)
        workflow_state = self._workflow_state.get(thread_id)

        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "checkpoint_count": len(checkpoints),
            "has_state": workflow_state is not None,
        }

        if not checkpoints:
            validation_result["valid"] = False
            validation_result["errors"].append(
                {
                    "code": "no_checkpoints",
                    "message": "No checkpoints found for workflow",
                    "severity": "error",
                }
            )

        if not workflow_state:
            validation_result["valid"] = False
            validation_result["errors"].append(
                {
                    "code": "no_state",
                    "message": "No workflow state found for workflow",
                    "severity": "error",
                }
            )

        # Check for inconsistent state
        for checkpoint in checkpoints:
            if checkpoint.thread_id != thread_id:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    {
                        "code": "inconsistent_thread_id",
                        "message": f"Checkpoint {checkpoint.checkpoint_id} has thread_id mismatch",
                        "severity": "error",
                    }
                )

        return validation_result

    def get_execution_summary(self, thread_id: str) -> Dict[str, Any]:
        """Get execution summary for a workflow.

        Args:
            thread_id: Workflow thread ID

        Returns:
            Dict containing execution summary
        """
        checkpoints = self.get_all_checkpoints_for_workflow(thread_id)
        workflow_state = self._workflow_state.get(thread_id)

        if not checkpoints:
            return {
                "thread_id": thread_id,
                "checkpoint_count": 0,
                "latest_checkpoint": None,
                "current_node": None,
                "completed_nodes": [],
                "state": None,
            }

        latest_checkpoint = max(checkpoints, key=lambda x: x.timestamp)

        return {
            "thread_id": thread_id,
            "checkpoint_count": len(checkpoints),
            "latest_checkpoint": {
                "checkpoint_id": latest_checkpoint.checkpoint_id,
                "timestamp": latest_checkpoint.timestamp.isoformat(),
                "node_name": latest_checkpoint.node_name,
            },
            "current_node": workflow_state.current_node if workflow_state else None,
            "completed_nodes": workflow_state.node_outputs.keys() if workflow_state else [],
            "state": workflow_state.state if workflow_state else None,
            "progress_percentage": (
                len(workflow_state.node_outputs) / 5 * 100 if workflow_state else 0
            ),  # Assuming 5 total nodes for demo
        }
