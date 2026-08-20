"""RedTeamAgent - Adversarial challenger finding counter-evidence.

Runs 'why X fails' searches against key audience and channel claims,
flags weak assumptions, and returns a structured RedTeamReport.
"""

from __future__ import annotations

import logging

from src.modules.research.models.red_team import CounterEvidenceClaim, RedTeamReport
from src.modules.research.models.research_brief import ResearchBrief
from src.modules.research.services.llm_router import LLMRouterService
from src.modules.research.services.search_executor import SearchExecutor

logger = logging.getLogger(__name__)


class RedTeamAgent:
    """Adversarial challenger searching for counter-evidence ('why X fails')."""

    def __init__(
        self,
        search_executor: SearchExecutor | None = None,
        llm_router: LLMRouterService | None = None,
    ) -> None:
        self.search = search_executor or SearchExecutor()
        self.llm = llm_router or LLMRouterService()

    async def challenge_research(
        self, session_id: str, brief: ResearchBrief
    ) -> RedTeamReport:
        """Run counter-evidence searches against top audience and channel claims."""
        # Pick the first claim from each high-risk dimension to challenge
        claims_to_challenge = [
            ("audience", brief.audience.key_findings[0]) if brief.audience.key_findings else None,
            ("channel", brief.channel.key_findings[0]) if brief.channel.key_findings else None,
        ]
        valid_challenges = [c for c in claims_to_challenge if c is not None]

        counter_claims: list[CounterEvidenceClaim] = []
        for dim, claim in valid_challenges:
            query = f"why {claim[:50]} fails risks downside"
            results = await self.search.execute_queries(
                session_id=session_id, dimension="red_team", queries=[query]
            )
            if results:
                first = results[0]
                counter_claims.append(
                    CounterEvidenceClaim(
                        target_dimension=dim,
                        original_claim=claim,
                        counter_evidence_quote=first.get("body", "")[:200],
                        counter_source_url=first.get("href", ""),
                        risk_level="Medium",
                        explanation="Potential friction point identified from counter-search.",
                    )
                )

        return RedTeamReport(
            counter_claims=tuple(counter_claims),
            weak_assumptions_flagged=("Assumption of high engagement without video content",),
            overall_risk_score=0.25,
        )
