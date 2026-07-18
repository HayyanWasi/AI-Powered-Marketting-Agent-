"""Reference Matcher Agent — loads brand style from reference posts/images.

This agent handles:
- Loading company profile data
- Extracting brand context
- Preparing reference posts for style matching

No LLM needed — pure data loading.
"""

from src.agents.base import BaseAgent, AgentResult
from src.agents.context import GenerationContext, BrandData


class ReferenceMatcherAgent(BaseAgent):
    """Loads brand data into the GenerationContext.

    This agent is the first step — it populates the BrandData
    from the company profile. All downstream agents use this data.
    """

    def __init__(self):
        super().__init__("reference_matcher")

    def execute(self, context: GenerationContext) -> AgentResult:
        """Load brand data into context.

        In production, this would read from the company profile.
        For now, the brand data is already in the context from
        the Context Builder.
        """
        if not context.brand.company_name:
            return AgentResult(
                success=False,
                context=context,
                message="No brand data in context. Company profile must be loaded before execution.",
            )

        self.logger.info(
            "Brand loaded: %s (%d reference images)",
            context.brand.company_name,
            len(context.brand.reference_image_urls),
        )

        return AgentResult(
            success=True,
            context=context,
            message=f"Brand context ready: {context.brand.company_name}",
        )
