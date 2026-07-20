"""Asset Generation Agent — creates branded visual content.

This agent:
- Takes image prompts from content drafts
- Generates images via Pollinations.ai (free)
- Applies brand conditioning

Requires: Pollinations.ai API (free, no key)
"""

from src.agents.base import BaseAgent, AgentResult
from src.agents.context import GenerationContext


class AssetGenerationAgent(BaseAgent):
    """Generates branded visual assets for content."""

    def __init__(self):
        super().__init__("asset_generator")

    def execute(self, context: GenerationContext) -> AgentResult:
        """Generate images for all content drafts."""
        if not context.content_drafts:
            return AgentResult(
                success=False,
                context=context,
                message="No content drafts to generate images for.",
            )

        # TODO: Call Pollinations.ai API for each image prompt
        # For now, log what would be generated
        for draft in context.content_drafts:
            self.logger.info(
                "Would generate image for slot %s: %s",
                draft.slot_id,
                draft.image_prompt[:60],
            )

        return AgentResult(
            success=True,
            context=context,
            message=f"Asset generation planned for {len(context.content_drafts)} drafts.",
        )
