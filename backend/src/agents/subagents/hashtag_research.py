"""Hashtag Research Sub-Agent — finds trending hashtags via DuckDuckGo.

No LLM needed — pure search.
"""

from src.agents.base import BaseAgent, AgentResult
from src.agents.context import GenerationContext
from dataclasses import replace


class HashtagResearchAgent(BaseAgent):
    """Researches trending hashtags for content topics."""

    def __init__(self):
        super().__init__("hashtag_research")

    def execute(self, context: GenerationContext) -> AgentResult:
        """Find relevant hashtags for the event and brand."""
        # TODO: Call DuckDuckGo search for trending hashtags
        # For now, return placeholder hashtags
        hashtags = (
            "#Marketing",
            "#Events",
            "#Networking",
            "#AI",
            "#Innovation",
            f"#{context.brand.company_name.replace(' ', '')}",
        )

        new_context = replace(
            context,
            hashtags=hashtags,
        )

        self.logger.info("Found %d hashtags", len(hashtags))

        return AgentResult(
            success=True,
            context=new_context,
            message=f"Found {len(hashtags)} relevant hashtags.",
        )
