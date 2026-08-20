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

from src.agents.base import AgentResult, BaseAgent
from src.agents.context import ContentDraft, GenerationContext
from src.services.cloudflare_image_service import (
    CloudflareImageService,
    CloudflareImageServiceError,
)


class AssetGenerationAgent(BaseAgent):
    """Generates branded visual assets for content."""

    def __init__(self, cloudflare_service: CloudflareImageService | None = None) -> None:
        """Initialize the agent.

        Args:
            cloudflare_service: Image generation backend. Constructed lazily
                per-run if not provided (so it can own/close its own client).
        """
        super().__init__("asset_generator")
        self._cloudflare = cloudflare_service

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
        """Generate an image for every content draft.

        Uses a single shared CloudflareImageService for the whole batch.
        On a per-draft failure, that draft keeps empty image fields
        (graceful degradation) rather than aborting the batch.

        Args:
            context: Immutable workflow snapshot.

        Returns:
            The list of drafts, each updated with image_url/image_model.
        """
        service = self._cloudflare or CloudflareImageService()
        own_service = self._cloudflare is None

        try:
            async with service:
                results: list[ContentDraft] = []
                for draft in context.content_drafts:
                    results.append(await self._generate_one(service, draft, context))
                return results
        finally:
            if own_service and self._cloudflare is None:
                # Service already closed by context manager
                pass

    async def _generate_one(
        self,
        service: CloudflareImageService,
        draft: ContentDraft,
        context: GenerationContext,
    ) -> ContentDraft:
        """Generate a single image and attach it to the draft.

        If reference images are available, uses img2img.
        Otherwise, falls back to text2img.

        Args:
            service: The Cloudflare service.
            draft: The content draft holding the base image prompt.
            context: Immutable workflow snapshot (for brand style/references).

        Returns:
            The draft, updated with image_url and image_model (empty on failure).
        """
        prompt = self._build_image_prompt(draft, context)

        try:
            # Try img2img if reference images are available
            reference_bytes = await self._get_reference_bytes(service, context)
            if reference_bytes:
                image_bytes = await service.generate_from_reference(
                    prompt=prompt,
                    reference_image_bytes=reference_bytes,
                    strength=0.6,
                )
                model = service.img2img_model
            else:
                # Fallback to text2img
                image_bytes = await service.generate_from_text(prompt=prompt)
                model = service.text2img_model

            # Convert bytes to base64 data URL for storage
            image_url = f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"

            self.logger.info(
                "Generated image for slot %s (model=%s, %d bytes)",
                draft.slot_id,
                model,
                len(image_bytes),
            )
            return replace(draft, image_url=image_url, image_model=model)

        except CloudflareImageServiceError as e:
            self.logger.warning("Image generation failed for slot %s: %s", draft.slot_id, e)
            return draft

    async def _get_reference_bytes(
        self,
        service: CloudflareImageService,
        context: GenerationContext,
    ) -> bytes | None:
        """Download the first reference image if available."""
        if not context.brand.reference_image_urls:
            return None

        url = context.brand.reference_image_urls[0]
        return await service.download_reference(url)

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
