"""Node Registry Service - Manages registered workflow nodes."""

from typing import Dict, Any, Callable

from .models.workflow_node import WorkflowNode


class NodeRegistry:
    """Registry for workflow nodes.

    The NodeRegistry is responsible for storing and managing registered
    workflow nodes. It provides lookup capabilities and validates that
    nodes are properly registered before execution.

    Each node is treated as a black-box executable unit with no knowledge
    of AI generation, campaigns, prompts, images, or business logic.
    """

    def __init__(self):
        self._nodes: Dict[str, WorkflowNode] = {}

    def register_node(self, node: WorkflowNode) -> None:
        """Register a workflow node.

        Args:
            node: WorkflowNode to register

        Raises:
            ValueError: If node with same name already exists
        """
        if node.name in self._nodes:
            raise ValueError(f"Node '{node.name}' already registered")
        self._nodes[node.name] = node

    def get_node(self, name: str) -> WorkflowNode:
        """Get a registered node by name.

        Args:
            name: Name of the node to retrieve

        Returns:
            Registered WorkflowNode

        Raises:
            ValueError: If node not found
        """
        if name not in self._nodes:
            raise ValueError(f"Node '{name}' not found")
        return self._nodes[name]

    def has_node(self, name: str) -> bool:
        """Check if a node is registered.

        Args:
            name: Name of the node to check

        Returns:
            True if node is registered, False otherwise
        """
        return name in self._nodes

    def list_nodes(self) -> Dict[str, WorkflowNode]:
        """List all registered nodes.

        Returns:
            Dictionary mapping node names to WorkflowNode objects
        """
        return self._nodes.copy()

    def execute_node(self, name: str, context) -> WorkflowContext:
        """Execute a registered node.

        Args:
            name: Name of the node to execute
            context: WorkflowContext for execution

        Returns:
            Updated WorkflowContext

        Raises:
            ValueError: If node not found
            Exception: If node execution fails
        """
        if not self.has_node(name):
            raise ValueError(f"Node '{name}' not found")

        node = self._nodes[name]

        try:
            result_context = node.handler(context)
            return result_context
        except Exception as e:
            # Wrap node execution exception
            from .models.execution_error import ExecutionError
            from datetime import datetime

            error = ExecutionError(
                node_name=name,
                error_code="node_failed",
                message=str(e),
                retry_count=0,
                timestamp=datetime.now(),
                recoverable=True,
            )

            error_context = context.add_error(error.to_dict())
            return error_context

    def clear(self) -> None:
        """Clear all registered nodes."""
        self._nodes.clear()

    def get_node_count(self) -> int:
        """Get the number of registered nodes.

        Returns:
            Number of registered nodes
        """
        return len(self._nodes)
