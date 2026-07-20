"""Workflow Node Model - Registered executable unit for workflow execution."""

from typing import Dict, Any, Callable, Optional

from ..retry_policy import RetryPolicy


class WorkflowNode:
    """A registered executable unit that receives an immutable WorkflowContext,
    performs a single task, and returns a new immutable WorkflowContext.

    Each node defines its own retry policy (retry count, retry delay, retry strategy).
    """

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable,
        retry_policy: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
        requires_approval: bool = False,
    ):
        """Initialize a new WorkflowNode.

        Args:
            name: Unique node name within the graph
            description: Human-readable description of node purpose
            handler: The executable function (registered at startup)
            retry_policy: Retry policy configuration
            timeout_seconds: Max execution time before timeout
            requires_approval: Whether node pauses for human approval

        Raises:
            ValueError: If name is empty or handler is not callable
        """
        if not name:
            raise ValueError("name cannot be empty")
        if not callable(handler):
            raise ValueError("handler must be callable")

        self.name = name
        self.description = description
        self.handler = handler
        self.retry_policy = retry_policy or {}
        self.timeout_seconds = timeout_seconds
        self.requires_approval = requires_approval

    def __repr__(self) -> str:
        return f"<WorkflowNode name={self.name} approval={self.requires_approval}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert WorkflowNode to dictionary.

        Returns:
            Dictionary representation of the WorkflowNode
        """
        return {
            "name": self.name,
            "description": self.description,
            "handler": self.handler.__name__ if hasattr(self.handler, "__name__") else "<lambda>",
            "retry_policy": self.retry_policy,
            "timeout_seconds": self.timeout_seconds,
            "requires_approval": self.requires_approval,
        }

    def to_workflow_node_data_model(self) -> Dict[str, Any]:
        """Convert to the data model representation used by WorkflowGraph.

        Returns:
            Dictionary formatted for WorkflowGraph
        """
        return {
            "name": self.name,
            "description": self.description,
            "handler": self.handler,
            "retry_policy": self.retry_policy,
            "timeout_seconds": self.timeout_seconds,
            "requires_approval": self.requires_approval,
        }
