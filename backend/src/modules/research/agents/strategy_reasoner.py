"""Agent 2: Strategy Reasoner (Decision Maker & Graph Linker).

Reads the unified ResearchBrief and saved Evidence Graph, generates strategic
decisions with explainable reasoning chains, and links (:Decision)-[:SUPPORTED_BY]->(:Evidence).
Also constructs pre-built ConversationTraces ("Why X?" engine).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.modules.research.models.evidence_graph import DecisionNode, EvidenceGraph
from src.modules.research.models.research_brief import ResearchBrief
from src.modules.research.models.traces import ConversationTrace, ConversationTraces
from src.modules.research.services.llm_router import LLMRouterService
from src.modules.research.services.neo4j_service import Neo4jService

logger = logging.getLogger(__name__)


class StrategyReasoner:
    """Agent 2: Decision Maker & Graph Linker."""

    def __init__(
        self,
        llm_router: LLMRouterService | None = None,
        neo4j: Neo4jService | None = None,
    ) -> None:
        self.llm = llm_router or LLMRouterService()
        self.neo4j = neo4j or Neo4jService()

    async def generate_strategy_decisions(
        self,
        session_id: UUID | str,
        brief: ResearchBrief,
    ) -> tuple[dict[str, Any], EvidenceGraph, ConversationTraces]:
        """Generate strategy deliverables and link Decision nodes in Neo4j + Postgres JSONB.

        Returns: (strategy_deliverables, evidence_graph, conversation_traces)
        """
        system_prompt = (
            "You are a Chief Marketing Strategist. Read the research brief evidence and construct "
            "decision nodes with explicit reasoning chains grounded strictly in live research."
        )
        user_prompt = f"""
Campaign Goal: {brief.user_goal}
Company: {brief.company_name}

Research Brief Summary:
- Market Findings: {list(brief.market.key_findings)}
- Audience Findings: {list(brief.audience.key_findings)}
- Competitor Findings: {list(brief.competitor.key_findings)}
- Channel Findings: {list(brief.channel.key_findings)}

Return ONLY valid JSON matching this schema:
{{
  "decisions": [
    {{
      "title": "Target LinkedIn carousels for B2B tech leads",
      "dimension": "channel",
      "rationale": "High executive engagement and 2.8x higher conversion on long-form carousels.",
      "evidence_ids": []
    }}
  ],
  "traces": [
    {{
      "question_pattern": "Why LinkedIn?",
      "decision_summary": "LinkedIn provides 3x higher conversion for decision makers.",
      "evidence_quotes": ["B2B executives report 80% lead conversion from LinkedIn content."],
      "source_urls": ["https://hubspot.com/reports/2025"]
    }}
  ]
}}
"""
        try:
            res = await self.llm.generate_json(system_prompt, user_prompt)
            raw_decisions = res.get("decisions", [])
            raw_traces = res.get("traces", [])
        except Exception as e:
            logger.warning("Strategy reasoner generation failed (%s)", e)
            raw_decisions = []
            raw_traces = []

        decisions_to_save: list[dict[str, Any]] = []
        decision_nodes: list[DecisionNode] = []

        for d in raw_decisions:
            node = DecisionNode(
                title=d.get("title", "Strategic Decision"),
                dimension=d.get("dimension", "core_strategy"),
                rationale=d.get("rationale", "Grounded in research brief evidence."),
                confidence_score=brief.overall_confidence_score,
            )
            decision_nodes.append(node)
            decisions_to_save.append(
                {
                    "decision_id": node.decision_id,
                    "title": node.title,
                    "dimension": node.dimension,
                    "rationale": node.rationale,
                    "evidence_ids": d.get("evidence_ids", []),
                }
            )

        # Link decisions in Neo4j + Postgres fallback
        await self.neo4j.link_decisions(session_id, decisions_to_save)

        # Build traces
        traces_list = [
            ConversationTrace(
                question_pattern=t.get("question_pattern", "Why this strategy?"),
                decision_summary=t.get("decision_summary", ""),
                evidence_quotes=tuple(t.get("evidence_quotes", [])),
                source_urls=tuple(t.get("source_urls", [])),
                confidence_score=brief.overall_confidence_score,
            )
            for t in raw_traces
        ]

        graph = EvidenceGraph(decisions=tuple(decision_nodes))
        traces = ConversationTraces(traces=tuple(traces_list))
        deliverables = {"decisions_count": len(decision_nodes), "status": "completed"}

        return deliverables, graph, traces
