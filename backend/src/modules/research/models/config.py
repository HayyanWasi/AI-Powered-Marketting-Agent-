"""Research tier configuration and budget parameters."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class ResearchTier(str, Enum):
    """Research depth tier."""

    QUICK = "Quick"
    STANDARD = "Standard"
    DEEP = "Deep"


_TIER_PARAMS: dict[ResearchTier, tuple[int, int, int, int, int, float, float, float]] = {
    ResearchTier.QUICK: (1, 5, 20, 15, 3, 4.0, 10.0, 20.0),
    ResearchTier.STANDARD: (2, 12, 50, 40, 5, 5.0, 12.0, 45.0),
    ResearchTier.DEEP: (3, 20, 80, 60, 5, 5.0, 15.0, 60.0),
}


class ResearchTierConfig(BaseModel):
    """Budget caps and execution limits per tier."""

    model_config = ConfigDict(frozen=True)

    tier: ResearchTier = ResearchTier.DEEP
    max_iterations: int = 3
    max_searches_per_dimension: int = 20
    hard_search_ceiling: int = 80
    max_llm_calls: int = 60
    sources_validated_per_query: int = 5
    per_search_timeout_sec: float = 5.0
    per_llm_timeout_sec: float = 15.0
    total_pipeline_timeout_sec: float = 60.0

    @classmethod
    def from_tier(cls, tier: str | ResearchTier) -> ResearchTierConfig:
        """Factory creating tier configuration from a tier name or enum."""
        tier_enum = ResearchTier(tier) if isinstance(tier, str) else tier
        iters, searches, ceiling, llm, sources, s_to, l_to, p_to = _TIER_PARAMS[tier_enum]
        return cls(
            tier=tier_enum,
            max_iterations=iters,
            max_searches_per_dimension=searches,
            hard_search_ceiling=ceiling,
            max_llm_calls=llm,
            sources_validated_per_query=sources,
            per_search_timeout_sec=s_to,
            per_llm_timeout_sec=l_to,
            total_pipeline_timeout_sec=p_to,
        )

