"""Workflow Context Module - Immutable execution state for workflow nodes."""

from datetime import datetime
from typing import Dict, Any, List, Optional

from ..models.execution_state import ExecutionState
from ..models.approval_status import ApprovalStatus
from ..models.execution_error import ExecutionError


class WorkflowContext:
    """Immutable execution state shared across workflow nodes.

    WorkflowContext is the core execution state used by the Workflow Engine to
    coordinate workflow execution. Each node receives an immutable WorkflowContext
    and returns a new WorkflowContext containing its outputs. Existing context
    is never modified in place.

    The WorkflowContext contains:
    - Workflow configuration
    - Initial workflow state
    - Registered node inputs
    - Runtime execution metadata

    This ensures deterministic execution and preserves checkpoint integrity.
    """

    def __init__(
        self,
        workflow_id: str,
        thread_id: str,
        state: ExecutionState = ExecutionState.PENDING,
        node_outputs: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        current_node: Optional[str] = None,
    ):
        """Initialize a new WorkflowContext.

        Args:
            workflow_id: Unique identifier for this workflow execution
            thread_id: LangGraph thread ID for checkpoint isolation
            state: Current execution state
            node_outputs: Accumulated outputs from completed nodes
            errors: List of execution errors
            metadata: Optional execution metadata
            current_node: Name of the currently executing node

        Raises:
            ValueError: If workflow_id is empty or state is invalid
        """
        if not workflow_id:
            raise ValueError("workflow_id cannot be empty")
        if not thread_id:
            raise ValueError("thread_id cannot be empty")
        if state not in ExecutionState.__members__.values():
            raise ValueError(f"Invalid execution state: {state}")

        self._workflow_id = workflow_id
        self._thread_id = thread_id
        self._state = state
        self._node_outputs = node_outputs or {}
        self._errors = errors or []
        self._metadata = metadata or {}
        self._current_node = current_node
        self._created_at = datetime.now()
        self._updated_at = datetime.now()

    def __repr__(self) -> str:
        return (
            f"<WorkflowContext id={self.workflow_id} state={self.state} node={self.current_node}>"
        )

    @property
    def workflow_id(self) -> str:
        """Get the workflow ID."""
        return self._workflow_id

    @property
    def thread_id(self) -> str:
        """Get the thread ID."""
        return self._thread_id

    @property
    def state(self) -> ExecutionState:
        """Get the current execution state."""
        return self._state

    @property
    def node_outputs(self) -> Dict[str, Any]:
        """Get the accumulated node outputs."""
        return self._node_outputs.copy()

    @property
    def errors(self) -> List[Dict[str, Any]]:
        """Get the list of errors."""
        return self._errors.copy()

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get the execution metadata."""
        return self._metadata.copy()

    @property
    def current_node(self) -> Optional[str]:
        """Get the current node name."""
        return self._current_node

    @property
    def created_at(self) -> datetime:
        """Get the creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Get the last update timestamp."""
        return self._updated_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert WorkflowContext to dictionary.

        Returns:
            Dictionary representation of the WorkflowContext
        """
        return {
            "workflow_id": self.workflow_id,
            "thread_id": self.thread_id,
            "state": self.state.value,
            "node_outputs": self.node_outputs,
            "errors": self.errors,
            "metadata": self.metadata,
            "current_node": self.current_node,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def update(
        self,
        state: Optional[ExecutionState] = None,
        node_outputs: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        current_node: Optional[str] = None,
    ) -> "WorkflowContext":
        """Create a new WorkflowContext with updated fields.

        This method creates a new WorkflowContext with updated fields while
        preserving the immutable contract. This is used to pass updated state
        from nodes back to the workflow engine.

        Args:
            state: Updated execution state (preserve if None)
            node_outputs: Updated node outputs (preserve if None)
            errors: Updated errors (preserve if None)
            metadata: Updated metadata (preserve if None)
            current_node: Updated current node (preserve if None)

        Returns:
            New WorkflowContext with updated fields
        """
        return WorkflowContext(
            workflow_id=self.workflow_id,
            thread_id=self.thread_id,
            state=state or self.state,
            node_outputs={**self.node_outputs, **(node_outputs or {})},
            errors=self.errors + (errors or []),
            metadata={**self.metadata, **(metadata or {})},
            current_node=current_node or self.current_node,
        )

    def add_error(self, error: Dict[str, Any]) -> "WorkflowContext":
        """Add an error to the workflow context.

        Args:
            error: Error dictionary with error details

        Returns:
            New WorkflowContext with error added
        """
        return self.update(errors=[*self.errors, error])

    def set_node_output(self, node_name: str, output: Any) -> "WorkflowContext":
        """Set the output of a node.

        Args:
            node_name: Name of the node
            output: Output value

        Returns:
            New WorkflowContext with node output added
        """
        return self.update(node_outputs={**self.node_outputs, node_name: output})

    def set_current_node(self, node_name: str) -> "WorkflowContext":
        """Set the current node being executed.

        Args:
            node_name: Name of the current node

        Returns:
            New WorkflowContext with current node updated
        """
        return self.update(current_node=node_name)

    def to_workflows_format(self) -> Dict[str, Any]:
        """Convert to workflow format for LangGraph compatibility.

        Returns:
            Dictionary formatted for LangGraph workflow execution
        """
        return {
            "workflow_id": self.workflow_id,
            "thread_id": self.thread_id,
            "state": self.state.value,
            "node_outputs": self.node_outputs,
            "current_node": self.current_node,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowContext":
        """Create a WorkflowContext from a dictionary.

        Args:
            data: Dictionary representation of a WorkflowContext

        Returns:
            WorkflowContext instance
        """
        from datetime import datetime

        return cls(
            workflow_id=data["workflow_id"],
            thread_id=data["thread_id"],
            state=data["state"],
            node_outputs=data.get("node_outputs", {}),
            errors=data.get("errors", []),
            metadata=data.get("metadata", {}),
            current_node=data.get("current_node"),
        )
