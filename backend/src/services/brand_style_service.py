import logging

from src.models.brand_style import BrandStyleContextInternal, PollinationsPrompt
from src.models.campaign_image import CampaignContext, CompanyProfile

logger = logging.getLogger(__name__)


class BrandStyleService:
    """Service for extracting brand context and building Pollinations prompts."""

    def extract_brand_context(self, profile: CompanyProfile) -> BrandStyleContextInternal:
        """
        Extract brand style context from company profile.

        Args:
            profile: CompanyProfile with brand fields

        Returns:
            BrandStyleContextInternal with formatted brand attributes
        """
        context = BrandStyleContextInternal()

        # Format color palette
        if profile.brand_colors:
            context.color_palette = ", ".join(profile.brand_colors)
            logger.debug("Extracted brand colors: %s", context.color_palette)

        # Use brand personality directly
        if profile.brand_personality:
            context.personality_descriptors = profile.brand_personality
            logger.debug("Extracted brand personality: %s", context.personality_descriptors)

        # Use style guide directly
        if profile.style_guide:
            context.style_guidance = profile.style_guide
            logger.debug("Extracted style guide: %s", context.style_guidance)

        # Format logo reference
        if profile.logo_url:
            context.logo_reference = f"logo style from {profile.logo_url}"
            logger.debug("Extracted logo reference: %s", context.logo_reference)

        # Include reference images
        if profile.reference_images:
            context.reference_image_urls = profile.reference_images
            logger.debug("Extracted %d reference images", len(profile.reference_images))

        return context

    def build_prompt(
        self,
        campaign_prompt: str,
        brand_context: BrandStyleContextInternal,
        campaign_context: CampaignContext | None = None,
    ) -> PollinationsPrompt:
        """
        Build a Pollinations prompt from campaign prompt and brand context.

        Args:
            campaign_prompt: The base campaign image prompt
            brand_context: Extracted brand style attributes
            campaign_context: Optional campaign context (platform, type, audience)

        Returns:
            PollinationsPrompt with base_prompt and model
        """
        # Build brand conditioning components
        brand_parts = []

        if brand_context.color_palette:
            brand_parts.append(f"brand colors {brand_context.color_palette}")

        if brand_context.personality_descriptors:
            brand_parts.append(f"{brand_context.personality_descriptors} style")

        if brand_context.style_guidance:
            brand_parts.append(brand_context.style_guidance)

        if brand_context.logo_reference:
            brand_parts.append(f"logo reference {brand_context.logo_reference}")

        # Include reference images in prompt if available
        if brand_context.reference_image_urls:
            for idx, url in enumerate(brand_context.reference_image_urls):
                brand_parts.append(f"reference image {idx + 1}: {url}")

        # Add campaign context if provided
        if campaign_context:
            if campaign_context.platform:
                brand_parts.append(f"optimized for {campaign_context.platform}")
            if campaign_context.campaign_type:
                brand_parts.append(f"{campaign_context.campaign_type} campaign")
            if campaign_context.target_audience:
                brand_parts.append(f"targeting {campaign_context.target_audience}")

        # Combine campaign prompt with brand conditioning
        if brand_parts:
            brand_conditioning = ", ".join(brand_parts)
            base_prompt = f"{campaign_prompt}, {brand_conditioning}"
        else:
            base_prompt = campaign_prompt
            logger.info("No brand information available, using campaign prompt only")

        # Negative prompt for quality control
        negative_prompt = (
            "watermark, text, signature, blurry, low quality, distorted, "
            "ugly, deformed, noisy, artifacts, oversaturated, cartoon, illustration"
        )

        logger.debug("Built Pollinations prompt: %s", base_prompt)

        return PollinationsPrompt(
            base_prompt=base_prompt,
            model="kontext",
            negative_prompt=negative_prompt,
        )

    def build_fallback_prompt(self, brand_context: BrandStyleContextInternal) -> PollinationsPrompt:
        """
        Build a branded fallback prompt.

        Args:
            brand_context: Extracted brand style attributes

        Returns:
            PollinationsPrompt for fallback image
        """
        brand_parts = []

        if brand_context.color_palette:
            brand_parts.append(f"brand colors {brand_context.color_palette}")

        if brand_context.personality_descriptors:
            brand_parts.append(f"{brand_context.personality_descriptors} style")

        if brand_context.style_guidance:
            brand_parts.append(brand_context.style_guidance)

        if brand_parts:
            prompt = (
                f"Professional branded placeholder, {', '.join(brand_parts)}, clean minimal design"
            )
        else:
            prompt = "Professional marketing placeholder, clean minimal design"

        negative_prompt = (
            "watermark, text, signature, blurry, low quality, distorted, "
            "ugly, deformed, noisy, artifacts"
        )

        logger.debug("Built fallback prompt: %s", prompt)

        return PollinationsPrompt(
            base_prompt=prompt,
            model="kontext",
            negative_prompt=negative_prompt,
        )
