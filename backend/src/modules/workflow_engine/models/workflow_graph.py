"""Workflow Graph Model - Complete workflow definition with nodes and connections."""

from typing import Dict, Any, List, Set
from datetime import datetime

from .workflow_node import WorkflowNode
from .workflow_context import WorkflowContext
from .circle_dependency_error import CircleDependencyError
from .missing_entry_node_error import MissingEntryNodeError


class WorkflowGraph:
    """Complete workflow definition containing registered nodes, execution edges,
    routing rules, and entry points.

    A WorkflowGraph represents the complete specification of a workflow,
    including all nodes, their connections, routing rules, and execution
    configuration. The graph is used to drive workflow execution through
    deterministic state transitions.

    The graph supports:
    - Direct edges between nodes for sequential execution
    - Conditional edges for data-dependent routing
    - Entry and terminal nodes for workflow boundaries
    - Cycle detection to prevent infinite loops
    """

    def __init__(
        self,
        graph_id: str,
        nodes: Dict[str, WorkflowNode],
        entry_point: str,
        edges: List[Dict[str, Any]],
        conditional_edges: List[Dict[str, Any]],
        terminal_nodes: List[str],
    ):
        """Initialize a new WorkflowGraph.

        Args:
            graph_id: Unique identifier for this graph definition
            nodes: Map of node name to node definition
            entry_point: Name of the first node to execute
            edges: Directed edges between nodes
            conditional_edges: Data-dependent routing rules
            terminal_nodes: Set of terminal node names

        Raises:
            MissingEntryNodeError: If entry node is missing
            ValueError: If node references in edges are invalid
            CircleDependencyError: If circular dependency is detected
        """
        self.graph_id = graph_id
        self.nodes = nodes
        self.entry_point = entry_point
        self.edges = edges
        self.conditional_edges = conditional_edges
        self.terminal_nodes = terminal_nodes

        # Validate graph structure
        self._validate_graph()

    def __repr__(self) -> str:
        return f"<WorkflowGraph id={self.graph_id} nodes={len(self.nodes)}>"

    @property
    def node_names(self) -> List[str]:
        """Get list of node names in the graph."""
        return list(self.nodes.keys())

    @property
    def execution_order(self) -> List[str]:
        """Get the execution order of nodes based on dependencies.

        Returns:
            List of node names in execution order
        """
        dependencies = self._build_dependency_graph()
        visited = set()
        temp_visited = set()
        order = []

        def dfs(node_name: str):
            if node_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {node_name}")
            if node_name in visited:
                return

            temp_visited.add(node_name)
            for dependency in dependencies.get(node_name, set()):
                dfs(dependency)
            temp_visited.remove(node_name)
            visited.add(node_name)
            order.append(node_name)

        try:
            dfs(self.entry_point)
        except ValueError:
            # Fall back to node order if topological sort fails
            order = self.node_names

        return order

    @property
    def node_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get node configurations for routing.

        Returns:
            Dictionary mapping node names to their configurations
        """
        configs = {}
        for node_name, node in self.nodes.items():
            configs[node_name] = {
                "name": node.name,
                "description": node.description,
                "requires_approval": node.requires_approval,
                "timeout_seconds": node.timeout_seconds,
                "retry_policy": node.retry_policy,
            }
        return configs

    def get_terminal_nodes(self) -> List[str]:
        """Get the terminal nodes in the graph.

        Returns:
            List of terminal node names
        """
        return self.terminal_nodes.copy()

    def is_terminal_node(self, node_name: str) -> bool:
        """Check if a node is a terminal node.

        Args:
            node_name: Node name to check

        Returns:
            True if node is terminal, False otherwise
        """
        return node_name in self.terminal_nodes

    def has_conditional_edge(self, source_node: str) -> bool:
        """Check if a node has conditional edges.

        Args:
            source_node: Node name to check

        Returns:
            True if node has conditional edges, False otherwise
        """
        return any(edge["source"] == source_node for edge in self.conditional_edges)

    def get_conditional_edges(self, source_node: str) -> List[Dict[str, Any]]:
        """Get conditional edges for a source node.

        Args:
            source_node: Source node name

        Returns:
            List of conditional edges for the source node
        """
        return [edge for edge in self.conditional_edges if edge["source"] == source_node]

    def to_dict(self) -> Dict[str, Any]:
        """Convert WorkflowGraph to dictionary.

        Returns:
            Dictionary representation of the WorkflowGraph
        """
        return {
            "graph_id": self.graph_id,
            "nodes": {name: node.to_dict() for name, node in self.nodes.items()},
            "entry_point": self.entry_point,
            "edges": self.edges,
            "conditional_edges": self.conditional_edges,
            "terminal_nodes": self.terminal_nodes,
        }

    def validate_workflow(self) -> Dict[str, Any]:
        """Validate workflow structure and logic.

        Returns:
            Dict containing validation results and warnings
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "graph_info": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "conditional_edge_count": len(self.conditional_edges),
                "terminal_node_count": len(self.terminal_nodes),
                "entry_point": self.entry_point,
            },
        }

        # Validate entry point
        if not self.entry_point:
            validation_result["valid"] = False
            validation_result["errors"].append(
                {
                    "code": "missing_entry_node",
                    "message": "Entry point is missing",
                    "severity": "error",
                }
            )

        if self.entry_point and self.entry_point not in self.nodes:
            validation_result["valid"] = False
            validation_result["errors"].append(
                {
                    "code": "invalid_entry_node",
                    "message": f"Entry node '{self.entry_point}' not found",
                    "severity": "error",
                }
            )

        # Validate terminal nodes
        for terminal_node in self.terminal_nodes:
            if terminal_node not in self.nodes:
                validation_result["warnings"].append(
                    {
                        "code": "invalid_terminal_node",
                        "message": f"Terminal node '{terminal_node}' not found in nodes",
                        "severity": "warning",
                    }
                )

        # Detect circular dependencies
        try:
            cycles = self.detect_cycles()
            if cycles:
                validation_result["valid"] = False
                for cycle in cycles:
                    validation_result["errors"].append(
                        {
                            "code": "circular_dependency",
                            "message": f"Circular dependency detected: {' -> '.join(cycle)}",
                            "severity": "error",
                        }
                    )
        except ValueError as e:
            validation_result["valid"] = False
            validation_result["errors"].append(
                {
                    "code": "circular_dependency",
                    "message": str(e),
                    "severity": "error",
                }
            )

        # Validate edge references
        for edge in self.edges:
            if edge["source"] not in self.nodes:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    {
                        "code": "invalid_source_node",
                        "message": f"Edge references undefined source node '{edge['source']}'",
                        "severity": "error",
                    }
                )
            if edge["target"] not in self.nodes:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    {
                        "code": "invalid_target_node",
                        "message": f"Edge references undefined target node '{edge['target']}'",
                        "severity": "error",
                    }
                )

        for edge in self.conditional_edges:
            if edge["source"] not in self.nodes:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    {
                        "code": "invalid_source_node",
                        "message": f"Conditional edge references undefined source node '{edge['source']}'",
                        "severity": "error",
                    }
                )

        return validation_result

    def detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies in workflow graph.

        Returns:
            List of cycle paths found
        """
        cycles = []
        visited = set()
        path = []
        path_set = set()

        def dfs(node_name: str):
            if node_name in path_set:
                cycle_start = path.index(node_name)
                cycles.append(path[cycle_start:] + [node_name])
                return

            if node_name in visited:
                return

            visited.add(node_name)
            path.append(node_name)
            path_set.add(node_name)

            # Check outgoing edges
            for edge in self.edges:
                if edge["source"] == node_name:
                    dfs(edge["target"])

            for edge in self.conditional_edges:
                if edge["source"] == node_name:
                    dfs(edge["target"])

            path.pop()
            path_set.remove(node_name)

        for node_name in self.node_names:
            if node_name not in visited:
                dfs(node_name)

        return cycles

    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build dependency graph for topological sorting.

        Returns:
            Dictionary mapping node names to their dependencies
        """
        dependencies = {node_name: set() for node_name in self.node_names}

        # Add dependencies from edges
        for edge in self.edges:
            if edge["target"] in dependencies:
                dependencies[edge["target"]].add(edge["source"])

        return dependencies

    def _validate_graph(self) -> None:
        """Validate graph structure and detect issues.

        Raises:
            MissingEntryNodeError: If entry node is missing
            ValueError: If other validation errors occur
            CircleDependencyError: If circular dependency is detected
        """
        if not self.entry_point:
            raise MissingEntryNodeError("Entry point is missing")

        if self.entry_point not in self.nodes:
            raise MissingEntryNodeError(f"Entry node '{self.entry_point}' not found")

        # Check all edges
        for edge in self.edges:
            if edge["source"] not in self.nodes:
                raise ValueError(f"Source node '{edge['source']}' not found")
            if edge["target"] not in self.nodes:
                raise ValueError(f"Target node '{edge['target']}' not found")

        # Check conditional edges
        for edge in self.conditional_edges:
            if edge["source"] not in self.nodes:
                raise ValueError(f"Source node '{edge['source']}' not found")

        # Detect circular dependencies
        cycles = self.detect_cycles()
        if cycles:
            cycle_paths = []
            for cycle in cycles:
                cycle_paths.append(" -> ".join(cycle))
            raise CircleDependencyError(f"Circular dependency detected: {', '.join(cycle_paths)}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowGraph":
        """Create a WorkflowGraph from a dictionary.

        Args:
            data: Dictionary representation of a WorkflowGraph

        Returns:
            WorkflowGraph instance
        """
        from .workflow_node import WorkflowNode
        from .retry_policy import RetryPolicy

        # Load nodes
        nodes = {}
        for node_name, node_data in data["nodes"].items():
            # Handle optional fields
            retry_policy = None
            if node_data.get("retry_policy"):
                retry_policy = RetryPolicy(**node_data["retry_policy"])

            nodes[node_name] = WorkflowNode(
                name=node_data["name"],
                description=node_data.get("description", ""),
                handler=node_data["handler"],
                retry_policy=retry_policy.__dict__ if retry_policy else None,
                timeout_seconds=node_data.get("timeout_seconds"),
                requires_approval=node_data.get("requires_approval", False),
            )

        return cls(
            graph_id=data["graph_id"],
            nodes=nodes,
            entry_point=data["entry_point"],
            edges=data.get("edges", []),
            conditional_edges=data.get("conditional_edges", []),
            terminal_nodes=data.get("terminal_nodes", []),
        )
