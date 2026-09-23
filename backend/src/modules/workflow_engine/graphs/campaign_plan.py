"""Campaign plan drafting graph — the specialist panel fan-out.

Constitution Principle V: orchestration is LangGraph. This graph fans out to
five specialists concurrently and joins at the chief strategist.

Execution runs in three independent provider lanes so the specialists progress
in parallel without ever putting two requests on the same single-GPU Ollama
endpoint:

  Lane A  (Ollama endpoint A, concurrency 1)  → channel_plan
  Lane B  (Ollama endpoint B, concurrency 1)  → measurement, positioning
  Lane C  (remote provider chain)             → audience_research, competitive

Each Ollama lane falls back to the canonical remote provider chain on a genuine
provider failure/timeout — never to the other lane's GPU. The chief strategist
runs only after all five specialists complete, preferring the (now-free) Lane A
Ollama endpoint with a remote fallback.

Unlike ``campaign_generation``, the state here is a TypedDict with a real
``operator.add`` reducer on ``sections``. Parallel nodes writing to a plain
dict state would clobber each other; the reducer is what makes the fan-out safe.
"""

from __future__ import annotations

import asyncio
import logging
import operator
import time
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from src.config.settings import settings
from src.modules.planning.agents import chief_strategist
from src.modules.planning.agents.panel import SPECIALISTS
from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import CampaignPlan
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

GRAPH_ID = "campaign_plan"

# Which lane each specialist runs in. The source provider does not change the
# requirement that all five outputs are produced and validated.
_LANE_ASSIGNMENT: dict[str, str] = {
    "channel_plan": "A",
    "measurement": "B",
    "positioning": "B",
    "audience_research": "C",
    "competitive": "C",
}

# Remote lane may run its two specialists concurrently; the Ollama lanes never
# exceed one in-flight request against their single GPU.
_REMOTE_LANE_CONCURRENCY = 2


class _LaneGate:
    """Caps concurrent provider calls within one lane and records timing.

    A lane's semaphore is what actually guarantees an Ollama GPU is never sent
    two requests at once (Lane A and Lane B are both size 1). ``max_active`` is
    kept for assertions/diagnostics; ``total`` sums wall-clock spent in the lane.
    """

    def __init__(self, lane: str, limit: int) -> None:
        self._sem = asyncio.Semaphore(limit)
        self.lane = lane
        self.limit = limit
        self.active = 0
        self.max_active = 0
        self.total = 0.0

    async def run(self, name: str, provider_intent: str, coro_fn):
        async with self._sem:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            start = time.perf_counter()
            logger.info(
                "Planning specialist starting: specialist=%s lane=%s provider=%s active_lane=%d",
                name,
                self.lane,
                provider_intent,
                self.active,
            )
            try:
                return await coro_fn()
            finally:
                self.total += time.perf_counter() - start
                self.active -= 1


class PlanState(TypedDict, total=False):
    """State threaded through the panel graph."""

    brief: PlanBrief
    # Every specialist appends one entry; the reducer merges concurrent writes.
    sections: Annotated[list[dict[str, Any]], operator.add]
    failures: Annotated[list[str], operator.add]
    plan: CampaignPlan | None


def _make_specialist_node(
    name: str,
    fn,
    lane_service: LLMService,
    gate: _LaneGate,
    primary_provider: str,
):
    """Wrap a specialist callable as a lane-routed graph node.

    The node acquires its lane gate (so an Ollama GPU is never double-booked),
    runs the specialist against that lane's LLMService, and logs which provider
    actually answered and whether a fallback was used. A failure records itself
    in ``failures`` and contributes no section — the draft is refused later
    rather than persisted partial.
    """

    async def node(state: PlanState) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            data = await gate.run(
                name, primary_provider, lambda: fn(state["brief"], llm=lane_service)
            )
            if not data:
                raise ValueError(f"Planning specialist {name} returned no data")
            actual = lane_service._last_provider or primary_provider
            # A fallback only happened when an Ollama-primary lane ended up served
            # by a remote provider. The remote lane (primary "remote") using
            # gemini/openrouter/groq is its intended behaviour, not a fallback.
            fallback_used = primary_provider == "ollama" and actual != "ollama"
            logger.info(
                "Planning specialist completed: specialist=%s lane=%s provider=%s "
                "duration=%.1fs fallback_used=%s",
                name,
                gate.lane,
                actual,
                time.perf_counter() - start,
                fallback_used,
            )
            return {"sections": [{"name": name, "data": data}]}
        except Exception as e:
            logger.error("Panel specialist %s failed: %s", name, e)
            return {"failures": [f"{name}: {e}"]}

    return node


def _build_lane_services() -> dict[str, LLMService]:
    """Construct the three lane services from planning-specific config.

    An unconfigured Ollama endpoint degrades that lane to the remote chain so a
    missing tunnel never silently drops a required specialist.
    """
    a_url = settings.planning_ollama_a_base_url.strip()
    b_url = settings.planning_ollama_b_base_url.strip()
    lane_a = (
        LLMService.planning_ollama_lane(a_url, settings.planning_ollama_a_model)
        if a_url
        else LLMService.planning_remote_lane()
    )
    lane_b = (
        LLMService.planning_ollama_lane(b_url, settings.planning_ollama_b_model)
        if b_url
        else LLMService.planning_remote_lane()
    )
    lane_c = LLMService.planning_remote_lane()
    return {"A": lane_a, "B": lane_b, "C": lane_c}


def _synthesize_node_factory(chief_service: LLMService, gates: dict[str, _LaneGate]):
    async def _synthesize_node(state: PlanState) -> dict[str, Any]:
        """Join the panel and reconcile it into one plan (chief on Lane A)."""
        panel = {entry["name"]: entry["data"] for entry in state.get("sections", [])}
        start = time.perf_counter()
        plan = await chief_strategist.synthesize(state["brief"], panel, llm=chief_service)
        chief_duration = time.perf_counter() - start
        actual = chief_service._last_provider or "assembly"
        logger.info(
            "lane_A_total=%.1fs lane_B_total=%.1fs lane_C_total=%.1fs "
            "chief_duration=%.1fs chief_provider=%s chief_fallback=%s",
            gates["A"].total,
            gates["B"].total,
            gates["C"].total,
            chief_duration,
            actual,
            actual not in ("ollama", "assembly"),
        )
        return {"plan": plan}

    return _synthesize_node


def compile_graph(tier: str = "Quick"):
    """Build and compile the three-lane panel graph.

    No checkpointer: a draft run is short-lived and its durable output is the
    plan row in Postgres, not graph state.
    """
    specialists = SPECIALISTS
    graph = StateGraph(PlanState)

    lane_services = _build_lane_services()
    gates = {
        "A": _LaneGate("A", 1),
        "B": _LaneGate("B", 1),
        "C": _LaneGate("C", _REMOTE_LANE_CONCURRENCY),
    }

    graph.add_node("start", lambda state: {})
    for name, fn in specialists.items():
        lane = _LANE_ASSIGNMENT.get(name, "C")
        service = lane_services[lane]
        primary = "ollama" if service.has_ollama_provider() else "remote"
        graph.add_node(name, _make_specialist_node(name, fn, service, gates[lane], primary))
        graph.add_edge("start", name)
        graph.add_edge(name, "synthesize")

    # Chief prefers Lane A (channel is done by the time all lanes finish, so its
    # Ollama GPU is free) with the remote chain as fallback.
    graph.add_node("synthesize", _synthesize_node_factory(lane_services["A"], gates))
    graph.set_entry_point("start")
    graph.add_edge("synthesize", END)
    return graph.compile()


def initial_state(brief: PlanBrief) -> PlanState:
    return {"brief": brief, "sections": [], "failures": [], "plan": None}
