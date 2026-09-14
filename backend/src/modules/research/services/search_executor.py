"""Multi-query search execution engine.

Executes search queries concurrently with:
- Concurrency limiting via asyncio.Semaphore(3)
- 5.0 second per-search timeout
- SHA256 response caching via CacheService
- Audit logging via PostgresService
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from src.config.settings import settings
from src.modules.research.services.cache_service import CacheService
from src.modules.research.services.postgres_service import PostgresService

logger = logging.getLogger(__name__)


class SearchExecutor:
    """Executes multi-query web searches concurrently."""

    def __init__(
        self,
        postgres: PostgresService | None = None,
        cache: CacheService | None = None,
        concurrency: int = 3,
        per_search_timeout_sec: float | None = None,
    ) -> None:
        self.postgres = postgres or PostgresService()
        self.cache = cache or CacheService.get_instance()
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout_sec = per_search_timeout_sec or getattr(settings, "ddgs_timeout_seconds", 15.0)

    async def execute_queries(
        self,
        session_id: UUID | str,
        dimension: str,
        queries: list[str],
    ) -> list[dict[str, Any]]:
        """Execute a list of queries concurrently, capped by Semaphore(3)."""

        async def _single_query(query: str) -> list[dict[str, Any]]:
            cache_key = CacheService.hash_key("search", query)
            cached = await self.cache.get(cache_key)
            if cached is not None:
                logger.debug("Search cache hit for query: %s", query)
                return cached

            async with self.semaphore:
                start = time.perf_counter()
                try:
                    # Run search in thread with timeout
                    results = await asyncio.wait_for(
                        asyncio.to_thread(self._run_search, query),
                        timeout=self.timeout_sec,
                    )
                except TimeoutError:
                    logger.warning(
                        "Search query timed out after %.1fs: %s", self.timeout_sec, query
                    )
                    results = []
                except Exception as e:
                    logger.warning("Search query failed (%s): %s", e, query)
                    results = []

                latency_ms = int((time.perf_counter() - start) * 1000)

                # Log audit record
                await self.postgres.log_search(
                    session_id=session_id,
                    dimension=dimension,
                    query=query,
                    provider="ddgs",
                    results_count=len(results),
                    latency_ms=latency_ms,
                )

                # Cache results for 1 hour (3600s)
                await self.cache.set(cache_key, results, ttl_seconds=3600)
                return results

        tasks = [_single_query(q) for q in queries]
        all_results_nested = await asyncio.gather(*tasks)

        # Flatten and deduplicate by URL
        seen_urls = set()
        flat_results = []
        for res_list in all_results_nested:
            for item in res_list:
                url = item.get("href") or item.get("url") or ""
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    flat_results.append(item)

        return flat_results

    def _run_search(self, query: str) -> list[dict[str, Any]]:
        """Synchronous search wrapper."""
        # Legacy DDGS search removed for V2.
        return []
