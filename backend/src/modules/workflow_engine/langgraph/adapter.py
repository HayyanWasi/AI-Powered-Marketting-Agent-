"""LangGraph Adapter — translates internal models to LangGraph StateGraph."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LangGraphAdapter:
    """Translates WorkflowGraph/WorkflowNode to LangGraph StateGraph."""

    def build_state_graph(self, nodes: dict, edges: list, conditional_edges: list) -> Any:
        try:
            from langgraph.graph import StateGraph
        except ImportError:
            raise ImportError("langgraph is required. Install with: pip install langgraph")

        graph = StateGraph(dict)

        for name, node in nodes.items():
            handler = node.handler if hasattr(node, "handler") else node
            graph.add_node(name, handler)

        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            if target in nodes:
                graph.add_edge(source, target)

        for edge in conditional_edges:
            source = edge["source"]
            condition = edge.get("condition", lambda s: True)
            targets = edge.get("targets", {})
            graph.add_conditional_edges(
                source,
                condition,
                targets,
            )

        return graph
