"""GapDetector & Follow-up Query Generator Agent."""

from __future__ import annotations

import logging
from typing import Any

from src.modules.research.services.llm_router import LLMRouterService

logger = logging.getLogger(__name__)


class GapDetector:
    """Detects missing research evidence and generates targeted follow-up queries."""

    def __init__(self, llm_router: LLMRouterService | None = None) -> None:
        self.llm = llm_router or LLMRouterService()

    async def generate_initial_queries(
        self, dimension: str, user_goal: str, company_name: str
    ) -> list[str]:
        """Generate 3 targeted search queries for a dimension."""
        system_prompt = (
            "You are a Senior Research Analyst. Generate 2 specific, targeted web search queries "
            "to gather hard facts, benchmarks, and real-world evidence for marketing strategy."
        )
        user_prompt = f"""
Dimension: {dimension}
Campaign Goal: {user_goal}
Company: {company_name}

Return ONLY valid JSON matching this schema:
{{
  "queries": ["query 1", "query 2"]
}}
"""
        try:
            res = await self.llm.generate_json(system_prompt, user_prompt)
            queries = res.get("queries", [])
            if isinstance(queries, list) and len(queries) > 0:
                return queries[:2]
        except Exception as e:
            logger.warning(
                "Query generation failed for %s (%s); using default fallback", dimension, e
            )

        # Fallback queries if LLM fails
        return [
            f"{user_goal} {dimension} market research",
            f"{company_name} {user_goal} competitors {dimension}",
        ]

    async def generate_followup_queries(
        self,
        dimension: str,
        user_goal: str,
        current_evidence: list[dict[str, Any]],
        confidence_score: float,
    ) -> list[str]:
        """Generate 2 follow-up queries to fill evidence gaps when confidence < 4.0."""
        system_prompt = (
            "You are a Research Gap Analyst. Review current evidence and generate 2 follow-up queries "
            "to find missing proof points, counter-evidence, or data benchmarks."
        )
        user_prompt = f"""
Dimension: {dimension}
Campaign Goal: {user_goal}
Current Confidence Score: {confidence_score} / 5.0
Current Evidence Collected: {len(current_evidence)} items

Return ONLY valid JSON matching this schema:
{{
  "followup_queries": ["query 1", "query 2"]
}}
"""
        try:
            res = await self.llm.generate_json(system_prompt, user_prompt)
            queries = res.get("followup_queries", [])
            if isinstance(queries, list):
                return queries[:2]
        except Exception as e:
            logger.warning("Followup query generation failed for %s (%s)", dimension, e)

        return []
