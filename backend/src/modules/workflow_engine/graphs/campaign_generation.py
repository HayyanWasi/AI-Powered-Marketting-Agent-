"""Campaign generation workflow graph — the single, real LangGraph-backed pipeline.

Constitution Principle V: workflow orchestration MUST be implemented using
LangGraph. This module is the only place that sequences the marketing agents;
the agents themselves (src/agents/*) remain plain, orchestration-free callables
that can run standalone (e.g. in unit tests) without this graph.

Constitution Principle VI: retry logic belongs exclusively to the Workflow
module.  Every hard-node wrapper includes built-in retry with exponential
backoff so callers never implement retry outside the pipeline.
"""

import asyncio
import logging
import time
from dataclasses import replace
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END

from src.agents.base import AgentResult
from src.agents.context import GenerationContext
from src.agents.reference_matcher import ReferenceMatcherAgent
from src.agents.strategy import StrategyAgent
from src.agents.campaign_planner import CampaignPlannerAgent
from src.agents.content_generator import ContentGenerationAgent
from src.agents.asset_generator import AssetGenerationAgent
from src.agents.validator import ValidationAgent
from src.agents.subagents.hashtag_research import HashtagResearchAgent
from src.agents.subagents.hook_analyzer import HookAnalyzerAgent
from src.agents.subagents.readability_scorer import ReadabilityScorerAgent
from src.modules.workflow_engine.langgraph.adapter import LangGraphAdapter
from src.modules.workflow_engine.langgraph.executor import LangGraphExecutor

logger = logging.getLogger(__name__)

GRAPH_ID = "campaign_generation"

# ── Retry configuration (Constitution Principle VI) ──────────────────────
# Retry logic lives inside the workflow pipeline, not outside.
_DEFAULT_MAX_RETRIES = 2
_DEFAULT_RETRY_DELAY_S = 1.0
_DEFAULT_BACKOFF_MULTIPLIER = 2.0

# Node names, in pipeline order. Hard nodes abort the workflow on failure;
# soft nodes (sub-agent checks) log a failure but never abort the pipeline —
# this mirrors the previous hand-rolled orchestrator's behavior exactly.
_HARD_NODES = (
    "reference_matcher",
    "strategy",
    "campaign_planner",
    "content_generator",
    "asset_generator",
    "validator",
)
_SOFT_NODES = ("hashtag_research", "hook_analyzer", "readability_scorer")


def _make_hard_node(
    agent,
    name: str,
    *,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    retry_delay_s: float = _DEFAULT_RETRY_DELAY_S,
    backoff_multiplier: float = _DEFAULT_BACKOFF_MULTIPLIER,
):
    """Wrap an agent as a LangGraph node with built-in retry.

    Retry logic is part of the workflow pipeline (Constitution VI).  On
    transient failure the node retries up to *max_retries* times with
    exponential back-off before marking the workflow as failed.
    """

    def node(state: dict) -> dict:
        last_result: AgentResult | None = None
        attempts = max_retries + 1

        for attempt in range(attempts):
            try:
                result: AgentResult = agent.execute(state["context"])
            except Exception as exc:
                # Treat exceptions as a failed agent result
                logger.warning(
                    "Node %s attempt %d/%d raised: %s",
                    name, attempt + 1, attempts, exc,
                )
                result = AgentResult(
                    success=False,
                    context=state["context"],
                    message=f"{name} raised {type(exc).__name__}: {exc}",
                )

            last_result = result

            if result.success:
                break

            # Retry on failure (except last attempt)
            if attempt < max_retries:
                delay = retry_delay_s * (backoff_multiplier ** attempt)
                logger.warning(
                    "Node %s failed (attempt %d/%d), retrying in %.1fs: %s",
                    name, attempt + 1, attempts, delay, result.message,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Node %s failed after %d attempts: %s",
                    name, attempts, result.message,
                )

        result = last_result
        log_entry = {
            "agent": name,
            "success": result.success,
            "message": result.message,
            "requires_human": result.requires_human,
            "attempts": min(attempt + 1, attempts),
        }
        if not result.success:
            return {
                "context": result.context,
                "log": (*state["log"], log_entry),
                "failed": True,
                "message": result.message,
            }
        return {
            "context": result.context,
            "log": (*state["log"], log_entry),
            "failed": False,
            "message": result.message,
        }

    return node


def _make_soft_node(
    agent,
    name: str,
    *,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    retry_delay_s: float = _DEFAULT_RETRY_DELAY_S,
    backoff_multiplier: float = _DEFAULT_BACKOFF_MULTIPLIER,
):
    """Wrap a sub-agent as a node whose failure never halts the pipeline.

    Soft nodes still retry internally (Constitution VI) but swallow the
    final failure so the pipeline continues.
    """

    def node(state: dict) -> dict:
        last_result: AgentResult | None = None
        attempts = max_retries + 1

        for attempt in range(attempts):
            try:
                result: AgentResult = agent.execute(state["context"])
            except Exception as exc:
                logger.warning(
                    "Soft node %s attempt %d/%d raised: %s",
                    name, attempt + 1, attempts, exc,
                )
                result = AgentResult(
                    success=False,
                    context=state["context"],
                    message=f"{name} raised {type(exc).__name__}: {exc}",
                )

            last_result = result

            if result.success:
                break

            if attempt < max_retries:
                delay = retry_delay_s * (backoff_multiplier ** attempt)
                logger.warning(
                    "Soft node %s failed (attempt %d/%d), retrying in %.1fs: %s",
                    name, attempt + 1, attempts, delay, result.message,
                )
                time.sleep(delay)

        result = last_result
        log_entry = {
            "agent": name,
            "success": result.success,
            "message": result.message,
            "requires_human": result.requires_human,
            "attempts": min(attempt + 1, attempts),
        }
        context = result.context if result.success else state["context"]
        if not result.success:
            logger.warning("Sub-agent %s failed after %d attempts (non-fatal): %s", name, attempts, result.message)
        return {**state, "context": context, "log": (*state["log"], log_entry)}

    return node


def _approve_strategy_node(state: dict) -> dict:
    """Auto-approve the strategy brief (human checkpoint in production).

    StateGraph(dict) has no per-key reducers, so a node's return value
    REPLACES the entire state rather than merging into it — every node must
    return the full state dict, not just the keys it changed.
    """
    context: GenerationContext = state["context"]
    approved_strategy = replace(context.strategy, approved=True)
    return {**state, "context": replace(context, strategy=approved_strategy)}


def _mark_complete_node(state: dict) -> dict:
    context: GenerationContext = state["context"]
    return {**state, "context": replace(context, current_step="complete")}


def _route_after_hard_node(state: dict) -> str:
    return "end" if state.get("failed") else "continue"


def build_agents(llm_service=None, cloudflare_service=None) -> dict:
    """Instantiate the fixed set of agents that make up the pipeline."""
    return {
        "reference_matcher": ReferenceMatcherAgent(),
        "strategy": StrategyAgent(llm_service=llm_service),
        "campaign_planner": CampaignPlannerAgent(),
        "content_generator": ContentGenerationAgent(llm_service=llm_service),
        "asset_generator": AssetGenerationAgent(cloudflare_service=cloudflare_service),
        "validator": ValidationAgent(),
        "hashtag_research": HashtagResearchAgent(),
        "hook_analyzer": HookAnalyzerAgent(),
        "readability_scorer": ReadabilityScorerAgent(),
    }


def compile_graph(agents: dict) -> Any:
    """Compile the campaign generation pipeline into a LangGraph app.

    Args:
        agents: Mapping of agent name to agent instance, as returned by
            build_agents().

    Returns:
        A compiled, checkpointed LangGraph app ready for ainvoke().
    """
    nodes: dict[str, Any] = {"approve_strategy": _approve_strategy_node, "mark_complete": _mark_complete_node}
    for name in _HARD_NODES:
        nodes[name] = _make_hard_node(agents[name], name)
    for name in _SOFT_NODES:
        nodes[name] = _make_soft_node(agents[name], name)

    # Note: LangGraphAdapter.build_state_graph only wires plain edges whose
    # target is itself a registered node (it filters `target in nodes`), so
    # the terminal `mark_complete -> END` edge is added directly below —
    # END is a sentinel, not a node.
    edges = [
        {"source": "approve_strategy", "target": "campaign_planner"},
        {"source": "hashtag_research", "target": "hook_analyzer"},
        {"source": "hook_analyzer", "target": "readability_scorer"},
        {"source": "readability_scorer", "target": "asset_generator"},
    ]

    conditional_edges = [
        {
            "source": "reference_matcher",
            "condition": _route_after_hard_node,
            "targets": {"continue": "strategy", "end": END},
        },
        {
            "source": "strategy",
            "condition": _route_after_hard_node,
            "targets": {"continue": "approve_strategy", "end": END},
        },
        {
            "source": "campaign_planner",
            "condition": _route_after_hard_node,
            "targets": {"continue": "content_generator", "end": END},
        },
        {
            "source": "content_generator",
            "condition": _route_after_hard_node,
            "targets": {"continue": "hashtag_research", "end": END},
        },
        {
            "source": "asset_generator",
            "condition": _route_after_hard_node,
            "targets": {"continue": "validator", "end": END},
        },
        {
            "source": "validator",
            "condition": _route_after_hard_node,
            "targets": {"continue": "mark_complete", "end": END},
        },
    ]

    graph = LangGraphAdapter().build_state_graph(nodes, edges, conditional_edges)
    graph.set_entry_point("reference_matcher")
    graph.add_edge("mark_complete", END)
    return graph.compile(checkpointer=MemorySaver())


def build_executor(llm_service=None, cloudflare_service=None) -> tuple[LangGraphExecutor, dict]:
    """Build agents, compile the graph, and register it on a fresh executor.

    Returns:
        (executor, agents) — agents are exposed so callers (e.g. the
        Orchestrator facade) can introspect them for logging/testing.
    """
    agents = build_agents(llm_service=llm_service, cloudflare_service=cloudflare_service)
    compiled = compile_graph(agents)
    executor = LangGraphExecutor()
    executor.register(GRAPH_ID, compiled)
    return executor, agents


def initial_state(context: GenerationContext) -> dict:
    return {"context": context, "log": (), "failed": False, "message": ""}
