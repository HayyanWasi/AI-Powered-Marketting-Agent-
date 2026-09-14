"""Unit and integration tests for the independent Autonomous Research Engine."""

import pytest

from src.modules.research.models.config import ResearchTier, ResearchTierConfig
from src.modules.research.models.evidence import ConfidenceScore
from src.modules.research.services.cache_service import CacheService
from src.modules.research.services.cost_controller import CostController


def test_research_tier_config():
    quick = ResearchTierConfig.from_tier("Quick")
    assert quick.tier == ResearchTier.QUICK
    assert quick.max_iterations == 1
    assert quick.hard_search_ceiling == 20

    deep = ResearchTierConfig.from_tier("Deep")
    assert deep.tier == ResearchTier.DEEP
    assert deep.max_iterations == 3
    assert deep.hard_search_ceiling == 80


def test_confidence_score_formula():
    conf = ConfidenceScore(
        corroboration=5.0,
        freshness=4.0,
        relevance=4.0,
        credibility=4.0,
    )
    # (5.0*0.35 = 1.75) + (4.0*0.25 = 1.0) + (4.0*0.25 = 1.0) + (4.0*0.15 = 0.6) = 4.35
    assert conf.composite_score == 4.35


def test_cost_controller():
    cfg = ResearchTierConfig.from_tier("Quick")
    controller = CostController(cfg)
    controller.record_search(5)
    controller.record_llm_call()

    assert controller.total_searches == 5
    assert controller.total_llm_calls == 1
    assert controller.check_search_budget() is True


@pytest.mark.asyncio
async def test_cache_service():
    cache = CacheService.get_instance()
    key = CacheService.hash_key("test", "query string")
    await cache.set(key, {"sample": "data"}, ttl_seconds=60)
    data = await cache.get(key)
    assert data == {"sample": "data"}
