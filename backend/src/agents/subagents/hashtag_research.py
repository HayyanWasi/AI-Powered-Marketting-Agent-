"""Hashtag Research Sub-Agent — finds trending hashtags via DuckDuckGo.

No LLM needed — pure search.
"""

import re
from dataclasses import replace

from src.agents.base import AgentResult, BaseAgent
from src.agents.context import GenerationContext
from src.services.search import GuestSearchService, SearchError


class HashtagResearchAgent(BaseAgent):
    """Researches trending hashtags for content topics."""

    def __init__(self, search_service: GuestSearchService | None = None):
        """Initialize the agent.

        Args:
            search_service: DuckDuckGo search backend. Constructed lazily
                if not provided.
        """
        super().__init__("hashtag_research")
        self._search_service = search_service

    def execute(self, context: GenerationContext) -> AgentResult:
        """Find relevant hashtags for the event and brand."""
        try:
            hashtags = self._search_hashtags(context)
        except Exception as e:
            self.logger.warning("Hashtag search failed (%s); using defaults", e)
            hashtags = self._default_hashtags(context)

        new_context = replace(
            context,
            hashtags=tuple(hashtags),
        )

        self.logger.info("Found %d hashtags", len(hashtags))

        return AgentResult(
            success=True,
            context=new_context,
            message=f"Found {len(hashtags)} relevant hashtags.",
        )

    def _search_hashtags(self, context: GenerationContext) -> list[str]:
        """Search for trending hashtags related to the event."""
        service = self._get_search_service()
        if service is None:
            return self._default_hashtags(context)

        # Build search queries
        queries = []
        if context.event.event_name:
            queries.append(f"{context.event.event_name} trending hashtags")
        if context.brand.company_name:
            queries.append(f"{context.brand.company_name} marketing hashtags")
        if context.event.platforms:
            platform = context.event.platforms[0]
            queries.append(f"{platform} trending hashtags {context.event.event_name}")

        all_hashtags: list[str] = []
        seen: set[str] = set()

        for query in queries[:2]:  # Limit to 2 queries to avoid rate limiting
            try:
                results = service.search(query)
                for result in results:
                    body = (result.get("body") or "").strip()
                    title = (result.get("title") or "").strip()
                    text = f"{title} {body}"
                    # Extract hashtags from search results
                    found = re.findall(r"#\w+", text)
                    for tag in found:
                        tag_lower = tag.lower()
                        if tag_lower not in seen:
                            seen.add(tag_lower)
                            all_hashtags.append(tag)
            except SearchError:
                continue

        # Add brand hashtag
        brand_tag = f"#{context.brand.company_name.replace(' ', '')}"
        if brand_tag.lower() not in seen:
            all_hashtags.append(brand_tag)

        # Ensure minimum hashtags
        if len(all_hashtags) < 3:
            all_hashtags.extend(self._default_hashtags(context))

        return all_hashtags[:10]  # Limit to 10 hashtags

    def _default_hashtags(self, context: GenerationContext) -> list[str]:
        """Return default hashtags when search fails."""
        defaults = ["#Marketing", "#Events", "#Networking"]
        if context.event.event_name:
            event_tag = f"#{context.event.event_name.replace(' ', '')}"
            defaults.append(event_tag)
        if context.brand.company_name:
            brand_tag = f"#{context.brand.company_name.replace(' ', '')}"
            defaults.append(brand_tag)
        return defaults

    def _get_search_service(self) -> GuestSearchService | None:
        """Return the search service, constructing it lazily."""
        if self._search_service is None:
            try:
                self._search_service = GuestSearchService()
            except Exception as e:
                self.logger.warning("Could not initialize search service (%s)", e)
                return None
        return self._search_service
