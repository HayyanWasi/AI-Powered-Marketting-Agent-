"""Marketing Agent Orchestrator — thin facade over the LangGraph pipeline.

Rule: All workflow nodes MUST consume only the GenerationContext.
No workflow node may re-read business data from persistent storage
during the same execution.

Actual node sequencing, routing, and checkpointing live in
src/modules/workflow_engine/graphs/campaign_generation.py (LangGraph), per
Constitution Principle V — "Workflow orchestration MUST be implemented using
LangGraph" / "The AI Generation module MUST NOT perform orchestration". This
class only adapts that graph to the pre-existing call/response shape used by
callers (API routes, tests, the smoke script).
"""

import logging
from dataclasses import replace
from enum import Enum

from src.agents.base import AgentResult
from src.agents.context import GenerationContext
from src.modules.workflow_engine.graphs import campaign_generation

logger = logging.getLogger(__name__)


class WorkflowPhase(Enum):
    """Phases of the marketing workflow."""

    INIT = "init"
    BRAND_LOADING = "brand_loading"
    STRATEGY = "strategy"
    STRATEGY_REVIEW = "strategy_review"
    PLANNING = "planning"
    CONTENT_GENERATION = "content_generation"
    SUB_AGENT_CHECKS = "sub_agent_checks"
    CONTENT_REVIEW = "content_review"
    ASSET_GENERATION = "asset_generation"
    VALIDATION = "validation"
    FINAL_REVIEW = "final_review"
    COMPLETE = "complete"


class Orchestrator:
    """Runs the campaign generation LangGraph pipeline.

    1. Creates the GenerationContext (snapshot) — via ContextBuilder, upstream
       of this class.
    2. Executes the LangGraph-compiled agent pipeline.
    3. Pauses at human checkpoints (approve_strategy/approve_content/reject_content).
    4. Never re-reads from database during execution.
    """

    def __init__(self, llm_service=None, cloudflare_service=None):
        """Create the orchestrator and compile its LangGraph pipeline.

        Args:
            llm_service: Optional LLMService injected into the content
                generator and strategy agent.
            cloudflare_service: Optional CloudflareImageService injected into
                the asset generator.
        """
        self._executor, self.agents = campaign_generation.build_executor(
            llm_service=llm_service, cloudflare_service=cloudflare_service
        )
        self.workflow_log: list[dict] = []

    async def execute(self, context: GenerationContext) -> AgentResult:
        """Execute the full marketing workflow via the LangGraph pipeline.

        Args:
            context: Immutable snapshot of all input data

        Returns:
            AgentResult with final context and status
        """
        logger.info("Starting workflow for context %s", context.context_id)

        final_state = await self._executor.execute(
            graph_id=campaign_generation.GRAPH_ID,
            initial_state=campaign_generation.initial_state(context),
            thread_id=context.context_id,
        )

        self.workflow_log = list(final_state["log"])
        final_context: GenerationContext = final_state["context"]

        if final_state.get("failed"):
            return AgentResult(
                success=False,
                context=final_context,
                message=final_state.get("message", "Workflow failed."),
            )

        logger.info("Workflow complete for context %s", context.context_id)

        return AgentResult(
            success=True,
            context=final_context,
            message="Workflow complete. Ready for publishing.",
        )

    def approve_strategy(self, context: GenerationContext) -> GenerationContext:
        """Human approves the strategy brief."""
        approved_strategy = replace(context.strategy, approved=True)
        return replace(context, strategy=approved_strategy)

    def approve_content(self, context: GenerationContext) -> GenerationContext:
        """Human approves the content drafts."""
        return replace(context, current_step="content_approved")

    def reject_content(self, context: GenerationContext, feedback: str) -> GenerationContext:
        """Human rejects content with feedback."""
        return replace(
            context,
            human_feedback=feedback,
            current_step="content_rejected",
        )
