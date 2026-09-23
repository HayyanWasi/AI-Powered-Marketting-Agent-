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
        self,
        dimension: str,
        user_goal: str,
        company_name: str,
        campaign_type: str = "",
        audience: str = "",
        category: str = "",
    ) -> list[str]:
        """Generate 3 targeted search queries for a dimension."""
        system_prompt = (
            "You are a Senior Research Analyst. Generate 2 specific, targeted web search queries "
            "to gather hard facts, benchmarks, and real-world evidence for marketing strategy. "
            "Base queries strictly on the structured campaign context (category, campaign type, audience, company). "
            "DO NOT concatenate long user prompts into search queries. "
            "DO NOT make assumptions about bootcamps, courses, or workshops unless the category "
            "or campaign type explicitly implies it."
        )
        user_prompt = f"""
Dimension: {dimension}
Campaign Goal: {user_goal}
Company: {company_name}
Campaign Type: {campaign_type}
Target Audience: {audience}
Category/Market: {category}

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

        # Fallback queries based on structured campaign context if LLM fails
        raw_subject = category or company_name or (user_goal.split()[:4] if user_goal else "")
        subject = " ".join(raw_subject) if isinstance(raw_subject, list) else str(raw_subject)
        subject = subject.strip() or "market"
        target = f" {audience.strip()}" if audience else ""

        if campaign_type == "app_launch":
            if dimension in ("competitor", "market"):
                return [
                    f"{subject} competing apps services alternatives",
                    f"{subject} app market trends{target}",
                ]
            elif dimension in ("audience", "channel"):
                return [
                    f"{subject} user acquisition channels strategy",
                    f"{subject} target audience problems behavior{target}",
                ]
            else:
                return [
                    f"{subject} app launch marketing benchmarks",
                    f"{subject} industry trends{target}",
                ]

        return [
            f"{subject} {dimension} benchmarks trends{target}",
            f"{company_name or subject} competitors {dimension}",
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
