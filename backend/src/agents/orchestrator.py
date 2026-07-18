"""Marketing Agent Orchestrator — coordinates all agents in sequence.

Rule: All workflow nodes MUST consume only the GenerationContext.
No workflow node may re-read business data from persistent storage
during the same execution.
"""

import logging
from enum import Enum

from src.agents.base import BaseAgent, AgentResult
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
    """Coordinates all marketing agents in a deterministic pipeline.

    The orchestrator:
    1. Creates the GenerationContext (snapshot)
    2. Runs agents in sequence
    3. Pauses at human checkpoints
    4. Handles rejection loops
    5. Never re-reads from database during execution
    """

    def __init__(self):
        self.agents = {
            "reference_matcher": ReferenceMatcherAgent(),
            "strategy": StrategyAgent(),
            "campaign_planner": CampaignPlannerAgent(),
            "content_generator": ContentGenerationAgent(),
            "asset_generator": AssetGenerationAgent(),
            "validator": ValidationAgent(),
            "hashtag_research": HashtagResearchAgent(),
            "hook_analyzer": HookAnalyzerAgent(),
            "readability_scorer": ReadabilityScorerAgent(),
        }
        self.workflow_log: list[dict] = []

    def execute(self, context: GenerationContext) -> AgentResult:
        """Execute the full marketing workflow.

        Args:
            context: Immutable snapshot of all input data

        Returns:
            AgentResult with final context and status
        """
        logger.info("Starting workflow for context %s", context.context_id)

        # Phase 1: Brand Loading
        result = self._run_agent("reference_matcher", context)
        if not result.success:
            return result
        context = result.context

        # Phase 2: Strategy (requires human approval)
        result = self._run_agent("strategy", context)
        if not result.success:
            return result
        context = result.context
        # Auto-approve for full workflow (human checkpoint in production)
        context = self.approve_strategy(context)

        # Phase 3: Planning
        result = self._run_agent("campaign_planner", context)
        if not result.success:
            return result
        context = result.context

        # Phase 4: Content Generation
        result = self._run_agent("content_generator", context)
        if not result.success:
            return result
        context = result.context

        # Phase 5: Sub-Agent Checks (parallel in production)
        for sub_agent_name in ["hashtag_research", "hook_analyzer", "readability_scorer"]:
            result = self._run_agent(sub_agent_name, context)
            if result.success:
                context = result.context

        # Phase 6: Validation
        result = self._run_agent("validator", context)
        if not result.success:
            return result
        context = result.context
        # PAUSE: Human must approve content before publishing

        # Phase 7: Asset Generation
        result = self._run_agent("asset_generator", context)
        if not result.success:
            return result
        context = result.context

        # Mark workflow complete
        from dataclasses import replace

        final_context = replace(context, current_step="complete")

        logger.info("Workflow complete for context %s", context.context_id)

        return AgentResult(
            success=True,
            context=final_context,
            message="Workflow complete. Ready for publishing.",
        )

    def _run_agent(self, agent_name: str, context: GenerationContext) -> AgentResult:
        """Run a single agent and log the result."""
        agent = self.agents[agent_name]
        logger.info("Running agent: %s", agent_name)

        result = agent.execute(context)

        self.workflow_log.append(
            {
                "agent": agent_name,
                "success": result.success,
                "message": result.message,
                "requires_human": result.requires_human,
            }
        )

        if not result.success:
            logger.error("Agent %s failed: %s", agent_name, result.message)

        return result

    def approve_strategy(self, context: GenerationContext) -> GenerationContext:
        """Human approves the strategy brief."""
        from dataclasses import replace

        approved_strategy = replace(context.strategy, approved=True)
        return replace(context, strategy=approved_strategy)

    def approve_content(self, context: GenerationContext) -> GenerationContext:
        """Human approves the content drafts."""
        from dataclasses import replace

        return replace(context, current_step="content_approved")

    def reject_content(self, context: GenerationContext, feedback: str) -> GenerationContext:
        """Human rejects content with feedback."""
        from dataclasses import replace

        return replace(
            context,
            human_feedback=feedback,
            current_step="content_rejected",
        )
