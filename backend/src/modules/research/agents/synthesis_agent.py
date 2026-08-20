"""SynthesisAgent - Merges 6 research worker outputs into a unified ResearchBrief."""

from __future__ import annotations

import logging

from src.modules.research.models.evidence import EvidenceItem
from src.modules.research.models.research_brief import DimensionSummary, ResearchBrief
from src.modules.research.services.llm_router import LLMRouterService

logger = logging.getLogger(__name__)


class SynthesisAgent:
    """Merges 6 worker outputs into a single unified ResearchBrief."""

    def __init__(self, llm_router: LLMRouterService | None = None) -> None:
        self.llm = llm_router or LLMRouterService()

    async def synthesize_brief(
        self,
        user_goal: str,
        company_name: str,
        dimension_data: dict[str, tuple[list[EvidenceItem], float, int]],
    ) -> ResearchBrief:
        """Build a ResearchBrief by aggregating each dimension's evidence, confidence, and findings."""
        summaries = {}
        all_scores = []

        for dim, (items, score, abandoned) in dimension_data.items():
            summaries[dim] = DimensionSummary(
                dimension=dim,
                key_findings=tuple(i.claim for i in items),
                evidence_items=tuple(items),
                confidence_score=score,
                sources_count=len(items),
                abandoned_sources_count=abandoned,
            )
            all_scores.append(score)

        overall_conf = round(sum(all_scores) / len(all_scores), 2) if all_scores else 3.5

        return ResearchBrief(
            user_goal=user_goal,
            company_name=company_name,
            market=summaries.get("market", DimensionSummary(dimension="market")),
            competitor=summaries.get("competitor", DimensionSummary(dimension="competitor")),
            audience=summaries.get("audience", DimensionSummary(dimension="audience")),
            content=summaries.get("content", DimensionSummary(dimension="content")),
            channel=summaries.get("channel", DimensionSummary(dimension="channel")),
            trend=summaries.get("trend", DimensionSummary(dimension="trend")),
            overall_confidence_score=overall_conf,
        )
