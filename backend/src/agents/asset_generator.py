"""Asset Generation Agent — creates branded visual content.

This agent:
- Takes image prompts from content drafts
- Uses Cloudflare Workers AI for image generation
- Uses img2img when reference images are available, text2img as fallback
- Downloads reference images and passes them as actual image bytes

Requires: CloudflareImageService (async).
"""

import asyncio
import base64
from dataclasses import replace
from typing import Any

from src.agents.base import AgentResult, BaseAgent
from src.agents.context import ContentDraft, GenerationContext
from src.services.pollinations_service import (
    PollinationsService,
)


class AssetGenerationAgent(BaseAgent):
    """Generates branded visual assets for content via Pollinations AI."""

    def __init__(
        self,
        image_service: Any | None = None,
        cloudflare_service: Any | None = None,
    ) -> None:
        """Initialize the agent.

        Args:
            image_service: Image generation backend (defaults to PollinationsService).
            cloudflare_service: Backward-compatibility alias for image_service.
        """
        super().__init__("asset_generator")
        self._service = image_service or cloudflare_service

    def execute(self, context: GenerationContext) -> AgentResult:
        """Generate images for all content drafts.

        Args:
            context: Immutable workflow snapshot.

        Returns:
            AgentResult with image_url/image_model attached to each draft.
        """
        if not context.content_drafts:
            return AgentResult(
                success=False,
                context=context,
                message="No content drafts to generate images for.",
            )

        drafts = asyncio.run(self._generate_all(context))

        generated = sum(1 for d in drafts if d.image_url)
        new_context = replace(
            context,
            content_drafts=tuple(drafts),
            current_step="assets_complete",
        )

        return AgentResult(
            success=True,
            context=new_context,
            message=f"Generated {generated}/{len(drafts)} images.",
        )

    async def _generate_all(self, context: GenerationContext) -> list[ContentDraft]:
        """Generate an image for every content draft."""
        service = self._service or PollinationsService()
        own_service = self._service is None

        try:
            if hasattr(service, "__aenter__"):
                async with service:
                    results: list[ContentDraft] = []
                    for draft in context.content_drafts:
                        results.append(await self._generate_one(service, draft, context))
                    return results
            else:
                results = []
                for draft in context.content_drafts:
                    results.append(await self._generate_one(service, draft, context))
                return results
        finally:
            if own_service and self._service is None:
                pass

    async def _generate_one(
        self,
        service: Any,
        draft: ContentDraft,
        context: GenerationContext,
    ) -> ContentDraft:
        """Generate a single image and attach it to the draft."""
        prompt = self._build_image_prompt(draft, context)

        try:
            if isinstance(service, PollinationsService):
                image_bytes, model = await service.generate_image_bytes(prompt=prompt)
            elif context.brand.reference_image_urls and hasattr(service, "generate_from_reference"):
                ref_bytes = await self._get_reference_bytes(service, context)
                if ref_bytes:
                    image_bytes = await service.generate_from_reference(
                        prompt=prompt,
                        reference_image_bytes=ref_bytes,
                        strength=0.6,
                    )
                    model = getattr(service, "img2img_model", "img2img")
                else:
                    image_bytes = await service.generate_from_text(prompt=prompt)
                    model = getattr(service, "text2img_model", "text2img")
            elif hasattr(service, "generate_from_text") and not isinstance(
                service, PollinationsService
            ):
                image_bytes = await service.generate_from_text(prompt=prompt)
                model = getattr(service, "text2img_model", "text2img")
            elif hasattr(service, "generate_image_bytes"):
                image_bytes, model = await service.generate_image_bytes(prompt=prompt)
            else:
                async with PollinationsService() as poll:
                    image_bytes, model = await poll.generate_image_bytes(prompt=prompt)

            # Convert bytes to base64 data URL for storage
            image_url = f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"

            self.logger.info(
                "Generated image for slot %s (model=%s, %d bytes)",
                draft.slot_id,
                model,
                len(image_bytes),
            )
            return replace(draft, image_url=image_url, image_model=model)

        except Exception as e:
            self.logger.warning("Image generation failed for slot %s: %s", draft.slot_id, e)
            return draft

    async def _get_reference_bytes(
        self,
        service: Any,
        context: GenerationContext,
    ) -> bytes | None:
        """Download the first reference image if available."""
        if not context.brand.reference_image_urls:
            return None

        url = context.brand.reference_image_urls[0]
        if hasattr(service, "download_reference"):
            return await service.download_reference(url)
        return None

    @staticmethod
    def _build_image_prompt(draft: ContentDraft, context: GenerationContext) -> str:
        """Compose the image prompt from draft + brand context.

        Args:
            draft: The content draft holding the base image prompt.
            context: Immutable workflow snapshot.

        Returns:
            The complete prompt string.
        """
        parts = [draft.image_prompt]

        brand = context.brand
        if brand.style_guide:
            parts.append(brand.style_guide)
        if brand.brand_tone:
            parts.append(f"{brand.brand_tone} style")

        return ", ".join(p for p in parts if p)
