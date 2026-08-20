"""Execution budget and cost controller manager."""

from __future__ import annotations

import logging

from src.modules.research.models.config import ResearchTierConfig

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Raised when execution limits or cost caps are reached."""


class CostController:
    """Tracks LLM calls, search queries, and total latency against tier caps."""

    def __init__(self, config: ResearchTierConfig) -> None:
        self.config = config
        self.total_searches: int = 0
        self.total_llm_calls: int = 0
        self.total_latency_ms: int = 0
        self.estimated_cost_usd: float = 0.0

    def record_search(self, count: int = 1, latency_ms: int = 0) -> None:
        """Record search executions."""
        self.total_searches += count
        self.total_latency_ms += latency_ms
        if self.total_searches > self.config.hard_search_ceiling:
            logger.warning(
                "Search ceiling reached (%d / %d)",
                self.total_searches,
                self.config.hard_search_ceiling,
            )

    def record_llm_call(self, latency_ms: int = 0, estimated_tokens: int = 500) -> None:
        """Record LLM calls and estimate cost."""
        self.total_llm_calls += 1
        self.total_latency_ms += latency_ms
        # Groq Llama 3 70B cost estimation (~$0.59 / 1M tokens)
        self.estimated_cost_usd += (estimated_tokens / 1_000_000) * 0.59

        if self.total_llm_calls > self.config.max_llm_calls:
            logger.warning(
                "LLM call budget limit reached (%d / %d)",
                self.total_llm_calls,
                self.config.max_llm_calls,
            )

    def check_search_budget(self) -> bool:
        return self.total_searches < self.config.hard_search_ceiling

    def check_llm_budget(self) -> bool:
        return self.total_llm_calls < self.config.max_llm_calls
