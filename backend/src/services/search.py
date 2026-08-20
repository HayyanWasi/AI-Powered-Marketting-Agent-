import logging
import time
from typing import Any

from ddgs import DDGS

from src.config.settings import settings

logger = logging.getLogger(__name__)

MAX_RESULTS = 7
INSUFFICIENT_RESULT_THRESHOLD = 3


class SearchError(Exception):
    pass


class GuestSearchService:
    def __init__(self, ddgs: DDGS | None = None):
        if ddgs is not None:
            self._ddgs = ddgs
        else:
            self._ddgs = DDGS(timeout=settings.ddgs_timeout_seconds)
        self._last_search_time: float = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_search_time
        min_interval = float(settings.ddgs_rate_limit_seconds)
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

    def _search(self, query: str) -> list[dict[str, Any]]:
        self._rate_limit()
        try:
            logger.info("[DDGS SEARCH] Executing query: '%s' (Max results: %d)", query, MAX_RESULTS)
            results: list[dict[str, Any]] = self._ddgs.text(query, max_results=MAX_RESULTS)
            self._last_search_time = time.time()
            logger.info("[DDGS SEARCH] Query '%s' returned %d results.", query, len(results))
            return results
        except Exception as e:
            self._last_search_time = time.time()
            logger.error("[DDGS SEARCH FAILED] Query '%s' failed: %s", query, e)
            raise SearchError(f"Search failed for '{query}': {e}") from e

    def search(self, guest_name: str, company_name: str | None = None) -> list[dict[str, Any]]:
        logger.info("=== [GUEST SEARCH INITIATED] ===")
        logger.info("Target: %s | Company: %s", guest_name, company_name)
        if company_name:
            query = f"{guest_name} {company_name}"
            results = self._search(query)
            if len(results) < INSUFFICIENT_RESULT_THRESHOLD:
                logger.info(
                    "[GUEST SEARCH] Company-based search returned < %d results; retrying with name only",
                    INSUFFICIENT_RESULT_THRESHOLD,
                )
                name_results = self._search(guest_name)
                seen_urls = {r.get("href", "") for r in results}
                for r in name_results:
                    if r.get("href", "") not in seen_urls:
                        results.append(r)
        else:
            results = self._search(guest_name)

        logger.info("=== [GUEST SEARCH COMPLETED] Total unique results: %d ===", len(results))
        for idx, res in enumerate(results[:3]):
            logger.info("   Result %d: %s...", idx + 1, str(res.get("body", ""))[:100])
        return results
