"""Campaign plan drafting graph — the specialist panel fan-out.

Constitution Principle V: orchestration is LangGraph. This graph fans out to
five specialists concurrently and joins at the chief strategist.

Unlike ``campaign_generation``, the state here is a TypedDict with a real
``operator.add`` reducer on ``sections``. Parallel nodes writing to a plain
dict state would clobber each other; the reducer is what makes the fan-out
safe.
"""

from __future__ import annotations

import logging
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from src.modules.planning.agents import chief_strategist
from src.modules.planning.agents.panel import SPECIALISTS
from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import CampaignPlan

logger = logging.getLogger(__name__)

GRAPH_ID = "campaign_plan"


class PlanState(TypedDict, total=False):
    """State threaded through the panel graph."""

    brief: PlanBrief
    # Every specialist appends one entry; the reducer merges concurrent writes.
    sections: Annotated[list[dict[str, Any]], operator.add]
    failures: Annotated[list[str], operator.add]
    plan: CampaignPlan | None


def _make_specialist_node(name: str, fn):
    """Wrap a specialist callable as a graph node.

    A failing specialist records itself in ``failures`` and contributes an
    empty section rather than aborting: the marketer can refine a thin section,
    but cannot refine a plan that never arrived.
    """

    async def node(state: PlanState) -> dict[str, Any]:
        try:
            data = await fn(state["brief"])
            return {"sections": [{"name": name, "data": data}]}
        except Exception as e:
            logger.error("Panel specialist %s failed: %s", name, e)
            return {"sections": [{"name": name, "data": {}}], "failures": [f"{name}: {e}"]}

    return node


async def _synthesize_node(state: PlanState) -> dict[str, Any]:
    """Join the panel and reconcile it into one plan."""
    panel = {entry["name"]: entry["data"] for entry in state.get("sections", [])}
    plan = await chief_strategist.synthesize(state["brief"], panel)
    return {"plan": plan}


def compile_graph():
    """Build and compile the panel graph.

    No checkpointer: a draft run is short-lived and its durable output is the
    plan row in Postgres, not graph state.
    """
    graph = StateGraph(PlanState)

    graph.add_node("start", lambda state: {})
    for name, fn in SPECIALISTS.items():
        graph.add_node(name, _make_specialist_node(name, fn))
        graph.add_edge("start", name)
        graph.add_edge(name, "synthesize")

    graph.add_node("synthesize", _synthesize_node)
    graph.set_entry_point("start")
    graph.add_edge("synthesize", END)
    return graph.compile()


def initial_state(brief: PlanBrief) -> PlanState:
    return {"brief": brief, "sections": [], "failures": [], "plan": None}
