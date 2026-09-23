"""Autonomous Research Engine Master Service (Independent Module Entry Point).

Drives the 3-stage execution pipeline:
1. Stage 1: Research Hunter (6 parallel worker search loops with 3-loop max cap)
2. Stage 2: Synthesis, Red Team Adversarial Challenge & Neo4j Evidence Graph creation
3. Stage 3: Strategy Reasoner (Decision maker & Graph linker)

Exposes `draft_research()` which can run completely standalone or be attached into
any application workflow.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import UUID, uuid4

from src.modules.research.agents.red_team_agent import RedTeamAgent
from src.modules.research.agents.research_hunter import ResearchHunter
from src.modules.research.agents.strategy_reasoner import StrategyReasoner
from src.modules.research.agents.synthesis_agent import SynthesisAgent
from src.modules.research.models.config import ResearchTierConfig
from src.modules.research.models.evidence import EvidenceItem
from src.modules.research.models.red_team import RedTeamReport
from src.modules.research.models.research_brief import ResearchBrief
from src.modules.research.services.cost_controller import CostController
from src.modules.research.services.llm_router import LLMRouterService
from src.modules.research.services.neo4j_service import Neo4jService
from src.modules.research.services.postgres_service import PostgresService
from src.modules.research.services.search_executor import SearchExecutor

logger = logging.getLogger(__name__)

_WORKERS = ("audience", "content", "trend")
_LLM_SEMAPHORE = asyncio.Semaphore(2)


class ResearchEngineService:
    """Master orchestrator engine for autonomous research."""

    def __init__(
        self,
        postgres: PostgresService | None = None,
        neo4j: Neo4jService | None = None,
        llm_router: LLMRouterService | None = None,
    ) -> None:
        self.postgres = postgres or PostgresService()
        self.neo4j = neo4j or Neo4jService(self.postgres)
        self.llm = llm_router or LLMRouterService()

        self.search = SearchExecutor(self.postgres)
        self.hunter = ResearchHunter(self.search, self.llm)
        self.synthesis = SynthesisAgent(self.llm)
        self.red_team = RedTeamAgent(self.search, self.llm)
        self.reasoner = StrategyReasoner(self.llm, self.neo4j)

    async def draft_research(
        self,
        user_goal: str,
        company_name: str = "",
        tier: str = "Quick",
        campaign_id: UUID | None = None,
        campaign_type: str = "",
        audience: str = "",
        category: str = "",
    ) -> dict[str, Any]:
        """Execute complete autonomous research pipeline.

        Args:
            user_goal: Free-text campaign goal.
            company_name: Brand/Company name.
            tier: Depth tier ("Quick", "Standard", "Deep").
            campaign_id: Optional campaign UUID for database association.
            campaign_type: Type of campaign (e.g. app_launch).
            audience: Target audience.
            category: Industry or market category.

        Returns:
            Dict payload with research_brief, evidence_graph, red_team_report,
            conversation_traces, and session_metrics.
        """
        start_time = time.perf_counter()
        tier_config = ResearchTierConfig.from_tier(tier)
        cost_controller = CostController(tier_config)

        # Create session audit log
        session_row = await self.postgres.create_session(campaign_id, tier_config.tier.value)
        session_id = UUID(session_row["id"]) if session_row.get("id") else uuid4()

        logger.info(
            "Starting Autonomous Research Engine session %s (Tier: %s)",
            session_id,
            tier_config.tier.value,
        )

        # ── STAGE 1: Research Hunter (6 Parallel Workers with Semaphore(3)) ──────
        semaphore = asyncio.Semaphore(3)

        async def _run_worker(dim: str) -> tuple[str, list[EvidenceItem], float, int]:
            async with semaphore:
                async with _LLM_SEMAPHORE:
                    items, conf, abandoned = await self.hunter.collect_dimension_evidence(
                        session_id=session_id,
                        dimension=dim,
                        user_goal=user_goal,
                        company_name=company_name,
                        tier_config=tier_config,
                        cost_controller=cost_controller,
                        campaign_type=campaign_type,
                        audience=audience,
                        category=category,
                    )
                return dim, items, conf, abandoned

        worker_results = await asyncio.gather(*(_run_worker(w) for w in _WORKERS))
        dimension_data = {
            dim: (items, conf, abandoned) for dim, items, conf, abandoned in worker_results
        }

        # ── STAGE 2: Synthesis, Red Team & Neo4j Evidence Graph Save ─────────────
        brief: ResearchBrief = await self.synthesis.synthesize_brief(
            user_goal=user_goal,
            company_name=company_name,
            dimension_data=dimension_data,
        )
        cost_controller.record_llm_call()

        # Save Evidence & Source nodes in Neo4j + Postgres JSONB fallback
        all_evidence_items = [
            item.to_dict() for items, _, _ in dimension_data.values() for item in items
        ]

        await self.neo4j.save_evidence_nodes(session_id, all_evidence_items)

        if tier_config.tier != "Quick":
            # Run Red Team Adversarial Challenge
            red_team_report: RedTeamReport = await self.red_team.challenge_research(
                session_id=str(session_id), brief=brief
            )
            cost_controller.record_llm_call()

            # ── STAGE 3: Strategy Reasoner & Decision Graph Linker ────────────────────
            deliverables, graph, traces = await self.reasoner.generate_strategy_decisions(
                session_id=session_id, brief=brief
            )
            cost_controller.record_llm_call()
        else:
            red_team_report = RedTeamReport(
                counter_claims=(), weak_assumptions_flagged=(), overall_risk_score=0.0
            )
            # Lightweight stubs
            from src.modules.research.models.strategy import AgentConversationTraces

            from src.modules.research.models.evidence_graph import EvidenceGraph

            graph = EvidenceGraph(nodes={}, edges=[])
            traces = AgentConversationTraces(agent_chats={})

        # Complete audit session log
        total_latency_ms = int((time.perf_counter() - start_time) * 1000)
        await self.postgres.complete_session(
            session_id=session_id,
            total_searches=cost_controller.total_searches,
            total_llm_calls=cost_controller.total_llm_calls,
            total_latency_ms=total_latency_ms,
            estimated_cost_usd=cost_controller.estimated_cost_usd,
        )

        logger.info(
            "Research session %s completed in %d ms (Searches: %d, LLM Calls: %d, Cost: $%.4f)",
            session_id,
            total_latency_ms,
            cost_controller.total_searches,
            cost_controller.total_llm_calls,
            cost_controller.estimated_cost_usd,
        )

        return {
            "session_id": str(session_id),
            "tier": tier_config.tier.value,
            "research_brief": brief.to_dict(),
            "evidence_graph": graph.to_dict(),
            "red_team_report": red_team_report.to_dict(),
            "conversation_traces": traces.to_dict(),
            "metrics": {
                "total_searches": cost_controller.total_searches,
                "total_llm_calls": cost_controller.total_llm_calls,
                "total_latency_ms": total_latency_ms,
                "estimated_cost_usd": cost_controller.estimated_cost_usd,
            },
        }
