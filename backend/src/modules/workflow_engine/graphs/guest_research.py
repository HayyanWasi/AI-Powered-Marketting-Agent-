"""Guest Research Graph - Autonomous ReAct loop for guest bio generation.

Uses DuckDuckGo search autonomously to find relevant context about a guest.
"""

from __future__ import annotations

import asyncio
import logging
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from src.services.llm import LLMService
from src.services.search import GuestSearchService

logger = logging.getLogger(__name__)

GRAPH_ID = "guest_research"


class GuestResearchState(TypedDict, total=False):
    """State for the guest research loop."""
    guest_name: str
    guest_title: str
    campaign_context: str

    # Accumulates across iterations (operator.add reducer)
    search_queries_run: Annotated[list[str], operator.add]
    # Accumulates results across iterations
    all_raw_results: Annotated[list[dict[str, Any]], operator.add]

    is_relevant: bool
    guest_profile: dict[str, Any]
    iterations: int


async def think_and_search_node(state: GuestResearchState) -> dict[str, Any]:
    """Decide on a search query and execute it."""
    guest_name = state.get("guest_name", "")
    guest_title = state.get("guest_title", "")
    campaign_context = state.get("campaign_context", "")
    iterations = state.get("iterations", 0)
    search_queries_run = state.get("search_queries_run") or []

    if iterations == 0:
        # First pass: use name + title together for specificity
        query = f"{guest_name} {guest_title}".strip()
    elif iterations == 1:
        # Second pass: add campaign context keywords for disambiguation
        context_keywords = campaign_context.replace("|", " ").replace(":", " ")[:40]
        query = f"{guest_name} {context_keywords}".strip()
    else:
        # Third pass: try just name + a generic professional qualifier
        query = f"{guest_name} professional speaker expert"

    # Avoid re-running the exact same query
    if query in search_queries_run:
        query = f"{guest_name} {guest_title} biography"

    logger.info("[GUEST RESEARCH AGENT] Iteration %d — Search query: '%s'", iterations + 1, query)

    results: list[dict[str, Any]] = []
    try:
        search_service = GuestSearchService()
        # Run the synchronous _search in a thread pool so we don't block the event loop
        results = await asyncio.get_event_loop().run_in_executor(
            None, search_service._search, query
        )
        logger.info("[GUEST RESEARCH AGENT] Got %d results.", len(results))
    except Exception as e:
        logger.error("[GUEST RESEARCH AGENT] Search failed: %s", e)

    return {
        "search_queries_run": [query],
        "all_raw_results": results,
        "iterations": iterations + 1,
    }


async def evaluate_node(state: GuestResearchState) -> dict[str, Any]:
    """Evaluate whether the accumulated results are good enough or we need another search."""
    iterations = state.get("iterations", 0)
    all_results = state.get("all_raw_results") or []

    # Safety: always stop at 3 iterations
    if iterations >= 3:
        logger.info("[GUEST RESEARCH AGENT] Max iterations reached. Forcing synthesis.")
        return {"is_relevant": True}

    if not all_results:
        logger.info("[GUEST RESEARCH AGENT] No results at all. Will retry search.")
        return {"is_relevant": False}

    # If we have at least 2 results, proceed — we don't want extra LLM calls on a hot path.
    # The synthesize_node uses campaign_context to filter the bio anyway.
    if len(all_results) >= 2:
        logger.info(
            "[GUEST RESEARCH AGENT] %d results found — sufficient for synthesis.", len(all_results)
        )
        return {"is_relevant": True}

    # 1 result: still usable, proceed
    logger.info("[GUEST RESEARCH AGENT] Only 1 result found — proceeding to synthesis.")
    return {"is_relevant": True}


async def synthesize_node(state: GuestResearchState) -> dict[str, Any]:
    """Synthesize the final bio from all accumulated search results."""
    logger.info("[GUEST RESEARCH AGENT] Synthesizing final bio...")
    all_results = state.get("all_raw_results") or []
    campaign_context = state.get("campaign_context", "")

    if not all_results:
        logger.warning("[GUEST RESEARCH AGENT] No results to synthesize — returning empty profile.")
        return {"guest_profile": {}}

    try:
        # LLMService.analyze_search_results is sync — safe to call directly
        profile_data = LLMService().analyze_search_results(
            all_results[:8],
            campaign_context=campaign_context,
        )
        logger.info(
            "[GUEST RESEARCH AGENT] Bio synthesized. Confidence: %s | Bio snippet: '%s'",
            profile_data.confidence_level,
            profile_data.professional_biography[:100],
        )
        return {"guest_profile": profile_data.model_dump()}
    except Exception as e:
        logger.error("[GUEST RESEARCH AGENT] Synthesis failed: %s", e)
        return {"guest_profile": {}}


def route_evaluation(state: GuestResearchState) -> str:
    """Route based on the evaluation result."""
    if state.get("is_relevant", False):
        return "synthesize"
    return "think_and_search"


# ── Build the graph ──────────────────────────────────────────────────────────
builder = StateGraph(GuestResearchState)

builder.add_node("think_and_search", think_and_search_node)
builder.add_node("evaluate", evaluate_node)
builder.add_node("synthesize", synthesize_node)

builder.set_entry_point("think_and_search")

builder.add_edge("think_and_search", "evaluate")
builder.add_conditional_edges(
    "evaluate",
    route_evaluation,
    {
        "synthesize": "synthesize",
        "think_and_search": "think_and_search",
    },
)
builder.add_edge("synthesize", END)

guest_research_graph = builder.compile()
