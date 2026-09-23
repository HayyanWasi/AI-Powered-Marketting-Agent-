"""Agent 1: Research Hunter (Live Data Collector).

Executes up to 3 autonomous search loops across 6 worker dimensions:
(Market, Competitor, Audience, Content, Channel, Trend).
Applies explicit confidence scoring and logs source abandonments.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.modules.research.agents.gap_detector import GapDetector
from src.modules.research.models.config import ResearchTierConfig
from src.modules.research.models.evidence import ConfidenceScore, EvidenceItem, SourceItem
from src.modules.research.services.cost_controller import CostController
from src.modules.research.services.llm_router import LLMRouterService
from src.modules.research.services.search_executor import SearchExecutor

logger = logging.getLogger(__name__)


class ResearchHunter:
    """Agent 1: Multi-loop autonomous live data collector."""

    def __init__(
        self,
        search_executor: SearchExecutor | None = None,
        llm_router: LLMRouterService | None = None,
        gap_detector: GapDetector | None = None,
    ) -> None:
        self.search_executor = search_executor or SearchExecutor()
        self.llm = llm_router or LLMRouterService()
        self.gap_detector = gap_detector or GapDetector(self.llm)

    async def collect_dimension_evidence(
        self,
        session_id: UUID | str,
        dimension: str,
        user_goal: str,
        company_name: str,
        tier_config: ResearchTierConfig,
        cost_controller: CostController,
        campaign_type: str = "",
        audience: str = "",
        category: str = "",
    ) -> tuple[list[EvidenceItem], float, int]:
        """Execute autonomous search loop up to max_iterations (1 to 3 loops).

        Returns: (evidence_items, final_confidence_score, abandoned_sources_count)
        """
        evidence_collected: list[EvidenceItem] = []
        abandoned_sources_count = 0
        current_confidence = 1.0

        # Instantiate dimension-specific LLM router mapped to account key pool
        worker_llm = LLMRouterService(dimension=dimension)
        gap_detector = GapDetector(worker_llm)

        # Step 1: Initial query generation
        queries = await gap_detector.generate_initial_queries(
            dimension=dimension,
            user_goal=user_goal,
            company_name=company_name,
            campaign_type=campaign_type,
            audience=audience,
            category=category,
        )
        cost_controller.record_llm_call()

        # Step 2: Loop iterations (Quick: 1, Standard: 2, Deep: 3)
        for iteration in range(1, tier_config.max_iterations + 1):
            if not cost_controller.check_search_budget():
                logger.warning("Hard search cap reached; exiting loop early for %s", dimension)
                break

            # Execute search batch
            search_results = await self.search_executor.execute_queries(
                session_id=session_id, dimension=dimension, queries=queries
            )
            cost_controller.record_search(count=len(queries))

            # Filter top validated sources (ignore remainder)
            valid_results = search_results[: tier_config.sources_validated_per_query]
            abandoned_sources_count += max(0, len(search_results) - len(valid_results))

            # Extract evidence via LLM
            extracted, loop_confidence = await self._extract_evidence_items(
                dimension=dimension, results=valid_results, user_goal=user_goal, llm=worker_llm
            )
            cost_controller.record_llm_call()

            evidence_collected.extend(extracted)
            current_confidence = max(current_confidence, loop_confidence)

            # Check confidence target
            if current_confidence >= 4.0:
                logger.info(
                    "Dimension %s achieved target confidence %.2f in iteration %d",
                    dimension,
                    current_confidence,
                    iteration,
                )
                break

            # If confidence < 4.0 and iterations remain, generate follow-up queries
            if iteration < tier_config.max_iterations:
                queries = await gap_detector.generate_followup_queries(
                    dimension=dimension,
                    user_goal=user_goal,
                    current_evidence=[e.to_dict() for e in evidence_collected],
                    confidence_score=current_confidence,
                )
                cost_controller.record_llm_call()

                if not queries:
                    logger.info(
                        "GapDetector generated 0 follow-up queries for %s; max achievable confidence %.2f/4.0 reached",
                        dimension,
                        current_confidence,
                    )
                    break

        return evidence_collected, current_confidence, abandoned_sources_count

    async def _extract_evidence_items(
        self,
        dimension: str,
        results: list[dict[str, Any]],
        user_goal: str,
        llm: LLMRouterService | None = None,
    ) -> tuple[list[EvidenceItem], float]:
        """LLM extraction of claims, quotes, and confidence breakdown."""
        if not results:
            return [], 2.0

        llm_router = llm or self.llm

        snippets_text = "\n".join(
            f"- Title: {r.get('title', '')}\n  URL: {r.get('href', '')}\n  Body: {r.get('body', '')}"
            for r in results
        )

        system_prompt = (
            "You are a Research Evidence Collector. Extract key claims and verbatim quotes "
            "strictly from the provided web search snippets. Assign score values (1.0 to 5.0) for corroboration, "
            "freshness, relevance, and credibility. Do NOT invent facts or sources absent from the snippets. "
            "If snippets contain no relevant facts, return an empty claims array: {\"claims\": []}."
        )
        user_prompt = f"""
Dimension: {dimension}
Campaign Goal: {user_goal}
Web Snippets:
{snippets_text}

Return ONLY valid JSON matching this schema:
{{
  "claims": [
    {{
      "claim": "short claim statement",
      "quote": "verbatim snippet quote",
      "url": "source URL",
      "title": "source title",
      "corroboration": 4.0,
      "freshness": 4.5,
      "relevance": 4.0,
      "credibility": 4.0
    }}
  ]
}}
"""
        try:
            res = await llm_router.generate_json(system_prompt, user_prompt)
            raw_claims = res.get("claims", [])
            items: list[EvidenceItem] = []
            scores: list[float] = []

            for c in raw_claims:
                src = SourceItem(
                    url=c.get("url", ""),
                    title=c.get("title", "Web Source"),
                    domain=c.get("url", "").split("/")[2] if "//" in c.get("url", "") else "",
                )
                conf = ConfidenceScore(
                    corroboration=float(c.get("corroboration", 3.5)),
                    freshness=float(c.get("freshness", 4.0)),
                    relevance=float(c.get("relevance", 4.0)),
                    credibility=float(c.get("credibility", 4.0)),
                )
                item = EvidenceItem(
                    dimension=dimension,
                    claim=c.get("claim", ""),
                    quote=c.get("quote", ""),
                    source=src,
                    confidence=conf,
                )
                items.append(item)
                scores.append(conf.composite_score)

            avg_score = round(sum(scores) / len(scores), 2) if scores else 3.0
            return items, avg_score
        except Exception as e:
            logger.warning("Evidence extraction failed (%s)", e)
            return [], 2.5
