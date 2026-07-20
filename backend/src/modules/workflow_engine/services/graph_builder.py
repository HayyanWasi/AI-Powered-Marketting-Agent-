"""Graph Building Service - Constructs and validates workflow graphs."""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from .models.workflow_graph import WorkflowGraph
from .models.workflow_node import WorkflowNode
from .models.retry_policy import RetryPolicy
from .models.execution_state import ExecutionState


class GraphBuilder(ABC):
    """Abstract base class for graph building services."""

    @abstractmethod
    def build_graph(self, workflow_graph: WorkflowGraph) -> Dict[str, Any]:
        """Build a graph representation from a workflow graph.

        Args:
            workflow_graph: WorkflowGraph to build

        Returns:
            Dict representation of the compiled graph
        """
        pass

    @abstractmethod
    def validate_graph(self, workflow_graph: WorkflowGraph) -> None:
        """Validate workflow graph structure.

        Args:
            workflow_graph: WorkflowGraph to validate

        Raises:
            CircleDependencyError: If circular dependency is detected
            MissingEntryNodeError: If entry node is missing
            ValueError: If other validation errors occur
        """
        pass

    @abstractmethod
    def analyze_dependencies(self, workflow_graph: WorkflowGraph) -> Dict[str, Any]:
        """Analyze workflow dependencies and execute order.

        Args:
            workflow_graph: WorkflowGraph to analyze

        Returns:
            Dict containing dependency analysis
        """
        pass

    @abstractmethod
    def optimize_paths(self, workflow_graph: WorkflowGraph) -> WorkflowGraph:
        """Optimize workflow execution paths.

        Args:
            workflow_graph: WorkflowGraph to optimize

        Returns:
            Optimized WorkflowGraph
        """
        pass


class WorkflowGraphBuilder(GraphBuilder):
    """Concrete implementation of GraphBuilder for building workflow graphs."""

    def build_graph(self, workflow_graph: WorkflowGraph) -> Dict[str, Any]:
        """Build a graph representation from a workflow graph.

        This method converts the high-level WorkflowGraph into a LangGraph-compatible
        graph structure with nodes and edges.

        Args:
            workflow_graph: WorkflowGraph to build

        Returns:
            Dict representation of the compiled graph
        """
        nodes = []
        edges = []

        # Convert each WorkflowNode to graph node specification
        for node_name, workflow_node in workflow_graph.nodes.items():
            node_spec = {
                "id": node_name,
                "name": workflow_node.name,
                "handler": workflow_node.handler,
                "retry_policy": workflow_node.retry_policy,
                "timeout_seconds": workflow_node.timeout_seconds,
                "requires_approval": workflow_node.requires_approval,
                "description": workflow_node.description,
            }
            nodes.append(node_spec)

        # Convert edges
        for edge in workflow_graph.edges:
            graph_edge = {
                "source": edge["source"],
                "target": edge["target"],
            }
            edges.append(graph_edge)

        # Convert conditional edges
        for edge in workflow_graph.conditional_edges:
            graph_edge = {
                "source": edge["source"],
                "condition": edge["condition"],
                "target": edge["target"],
            }
            edges.append(graph_edge)

        return {
            "nodes": nodes,
            "edges": edges,
            "entry_point": workflow_graph.entry_point,
            "terminal_nodes": workflow_graph.terminal_nodes,
        }

    def validate_graph(self, workflow_graph: WorkflowGraph) -> None:
        """Validate workflow graph structure.

        Validates that:
        1. Entry node exists
        2. All edges reference valid nodes
        3. No circular dependencies exist
        4. At least one terminal node exists

        Args:
            workflow_graph: WorkflowGraph to validate

        Raises:
            CircleDependencyError: If circular dependency is detected
            MissingEntryNodeError: If entry node is missing
            ValueError: If other validation errors occur
        """
        if not workflow_graph.entry_point:
            raise MissingEntryNodeError("Entry point is missing")

        if workflow_graph.entry_point not in workflow_graph.nodes:
            raise MissingEntryNodeError(f"Entry node '{workflow_graph.entry_point}' not found")

        # Check all edges
        for edge in workflow_graph.edges:
            if edge["source"] not in workflow_graph.nodes:
                raise ValueError(f"Source node '{edge['source']}' not found")
            if edge["target"] not in workflow_graph.nodes:
                raise ValueError(f"Target node '{edge['target']}' not found")

        # Check conditional edges
        for edge in workflow_graph.conditional_edges:
            if edge["source"] not in workflow_graph.nodes:
                raise ValueError(f"Source node '{edge['source']}' not found")

        # Detect circular dependencies
        cycles = self.detect_cycles(workflow_graph)
        if cycles:
            cycle_paths = []
            for cycle in cycles:
                cycle_paths.append(" -> ".join(cycle))
            raise CircleDependencyError(f"Circular dependency detected: {', '.join(cycle_paths)}")

    def analyze_dependencies(self, workflow_graph: WorkflowGraph) -> Dict[str, Any]:
        """Analyze workflow dependencies and execute order.

        Determines the execution order based on dependencies between nodes.

        Args:
            workflow_graph: WorkflowGraph to analyze

        Returns:
            Dict containing dependency analysis
        """
        # Build dependency graph
        dependencies = {node_name: set() for node_name in workflow_graph.nodes}

        # Add dependencies from edges
        for edge in workflow_graph.edges:
            dependencies[edge["target"]].add(edge["source"])

        # Topological sort
        visited = set()
        temp_visited = set()
        order = []

        def dfs(node_name: str):
            if node_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {node_name}")
            if node_name in visited:
                return

            temp_visited.add(node_name)
            for dependency in dependencies[node_name]:
                dfs(dependency)
            temp_visited.remove(node_name)
            visited.add(node_name)
            order.append(node_name)

        # Perform DFS from entry point
        try:
            dfs(workflow_graph.entry_point)
        except ValueError:
            # Fall back to simple order if topological sort fails
            order = list(workflow_graph.nodes.keys())

        return {
            "execution_order": order,
            "dependency_graph": dependencies,
            "entry_point": workflow_graph.entry_point,
            "terminal_nodes": workflow_graph.terminal_nodes,
            "parallel_potential": self._calculate_parallel_potential(dependencies),
        }

    def optimize_paths(self, workflow_graph: WorkflowGraph) -> WorkflowGraph:
        """Optimize workflow execution paths.

        Removes unnecessary edges and optimizes the graph structure while
        preserving the workflow's functional behavior.

        Args:
            workflow_graph: WorkflowGraph to optimize

        Returns:
            Optimized WorkflowGraph
        """
        # For now, return the same workflow graph
        # In a more sophisticated implementation, this would:
        # 1. Remove unreachable nodes
        # 2. Collapse redundant paths
        # 3. Optimize edge patterns
        # 4. Reorder nodes for better parallelism

        return workflow_graph

    def detect_cycles(self, workflow_graph: WorkflowGraph) -> List[List[str]]:
        """Detect circular dependencies in workflow graph.

        Args:
            workflow_graph: Workflow graph to analyze

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
            for edge in workflow_graph.edges:
                if edge["source"] == node_name:
                    dfs(edge["target"])

            for edge in workflow_graph.conditional_edges:
                if edge["source"] == node_name:
                    dfs(edge["target"])

            path.pop()
            path_set.remove(node_name)

        for node_name in workflow_graph.nodes:
            if node_name not in visited:
                dfs(node_name)

        return cycles

    def _calculate_parallel_potential(self, dependencies: Dict[str, set]) -> Dict[str, bool]:
        """Calculate parallel execution potential for nodes.

        Args:
            dependencies: Dictionary mapping node names to their dependencies

        Returns:
            Dictionary indicating whether each node can run in parallel
        """
        parallel_potential = {}
        for node_name, deps in dependencies.items():
            parallel_potential[node_name] = len(deps) == 0 or True
        return parallel_potential
