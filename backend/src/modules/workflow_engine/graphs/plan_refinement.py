"""Plan refinement graph — one conversational turn over an existing plan.

Route the critique, fan out over *only* the targeted sections, then compose the
reply. Untargeted sections are never touched, so they come back identical.

Short-lived by design: durable state is the plan row in Postgres, not graph
state. A marketer's think-time between turns is unbounded, and ``MemorySaver``
would not survive a restart.
"""

from __future__ import annotations

import logging
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from src.modules.planning.agents import reviser
from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import CampaignPlan, PlanStatus

logger = logging.getLogger(__name__)

GRAPH_ID = "plan_refinement"


class RefinementState(TypedDict, total=False):
    """State for one refinement turn."""

    plan: CampaignPlan
    brief: PlanBrief
    critique: str

    route: Any
    # Each revise branch appends one entry; the reducer merges concurrent writes.
    revisions: Annotated[list[dict[str, Any]], operator.add]

    revised_plan: CampaignPlan
    sections_changed: tuple[str, ...]
    language: str
    is_approval: bool
    reply: str


async def _route_node(state: RefinementState) -> dict[str, Any]:
    route = await reviser.route_critique(state["plan"], state["critique"])
    return {"route": route, "language": route.language, "is_approval": route.is_approval}


async def _revise_node(state: RefinementState) -> dict[str, Any]:
    """Revise every targeted section concurrently.

    A single node fanning out internally rather than one graph node per
    section: which sections run is decided at runtime, and LangGraph's static
    topology cannot express that.
    """
    import asyncio

    route = state["route"]
    if not route.target_sections:
        return {"revisions": []}

    async def _one(name: str) -> dict[str, Any]:
        data = await reviser.revise_section(
            state["plan"],
            state["brief"],
            name,
            state["critique"],
            instructions=route.instructions.get(name, ""),
        )
        return {"name": name, "data": data}

    results = await asyncio.gather(*(_one(n) for n in route.target_sections))
    return {"revisions": list(results)}


async def _apply_node(state: RefinementState) -> dict[str, Any]:
    """Patch the revised sections onto the plan and bump the version."""
    patches = {r["name"]: r["data"] for r in state.get("revisions", []) if r["data"]}
    plan = state["plan"]

    if not patches:
        return {"revised_plan": plan, "sections_changed": ()}

    revised = plan.patch_sections(patches).model_copy(
        update={
            "version": plan.version + 1,
            "status": PlanStatus.REFINING,
            "language": state.get("language") or plan.language,
            "approved": False,
        }
    )
    return {"revised_plan": revised, "sections_changed": tuple(patches)}


async def _reply_node(state: RefinementState) -> dict[str, Any]:
    changed = state.get("sections_changed", ())
    valid_revisions = [r for r in state.get("revisions", []) if r.get("data")]
    if not valid_revisions:
        details = "Note: No sections were updated because the revision format was invalid. The original section contents were preserved."
    else:
        details = "\n".join(f"- {r['name']}: revised" for r in valid_revisions)
    reply = await reviser.compose_reply(
        state["critique"], changed, details, state.get("language") or "en"
    )
    return {"reply": reply}


def compile_graph():
    """Build and compile the refinement graph."""
    graph = StateGraph(RefinementState)
    graph.add_node("route", _route_node)
    graph.add_node("revise", _revise_node)
    graph.add_node("apply", _apply_node)
    graph.add_node("reply", _reply_node)

    graph.set_entry_point("route")
    graph.add_edge("route", "revise")
    graph.add_edge("revise", "apply")
    graph.add_edge("apply", "reply")
    graph.add_edge("reply", END)
    return graph.compile()


def initial_state(
    plan: CampaignPlan, brief: PlanBrief, critique: str
) -> RefinementState:
    return {"plan": plan, "brief": brief, "critique": critique, "revisions": []}
