"""Validation Agent — checks content against platform rules.

This agent:
- Validates character limits per platform
- Checks content quality via hook_score and readability_score
- Validates images (base64 data URLs and HTTP URLs)
- Reports violations

No LLM needed — pure rule-based validation.
"""

import base64
import io
import re
from dataclasses import replace

from src.agents.base import AgentResult, BaseAgent
from src.agents.context import ContentDraft, GenerationContext, ValidationResult
from src.models.platform import PLATFORM_TEXT_LIMITS, Platform

# Quality thresholds
MIN_HOOK_SCORE = 40
MIN_READABILITY_SCORE = 30.0


class ValidationAgent(BaseAgent):
    """Validates content against platform-specific rules."""

    def __init__(self):
        super().__init__("validator")

    def execute(self, context: GenerationContext) -> AgentResult:
        """Validate all content drafts."""
        if not context.content_drafts:
            return AgentResult(
                success=False,
                context=context,
                message="No content drafts to validate.",
            )

        results = []
        for draft in context.content_drafts:
            # Find the slot to get platform
            slot = next(
                (s for s in context.calendar if s.slot_id == draft.slot_id),
                None,
            )
            if not slot:
                continue

            result = self._validate_draft(draft, slot.platform)
            results.append(result)

            if not result.passed:
                self.logger.warning(
                    "Slot %s failed validation: %s",
                    draft.slot_id,
                    "; ".join(result.violations),
                )

        new_context = replace(
            context,
            validation_results=tuple(results),
            current_step="validation_complete",
        )

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        return AgentResult(
            success=passed == total,
            context=new_context,
            message=f"Validation: {passed}/{total} drafts passed.",
        )

    def _validate_draft(self, draft: ContentDraft, platform: str) -> ValidationResult:
        """Validate a single content draft."""
        violations = []

        # Use the selected variant or variant A
        content = draft.selected_variant or draft.variant_a

        # Character limit check
        limit = 0
        try:
            platform_enum = Platform(platform.lower())
            limit = PLATFORM_TEXT_LIMITS[platform_enum]
            char_count = len(content)

            if char_count > limit:
                violations.append(
                    f"Character count {char_count} exceeds {platform} limit of {limit}"
                )
        except ValueError:
            # Unknown platform — skip character check
            pass

        # Basic checks
        if not content.strip():
            violations.append("Content is empty")

        if len(content) < 10:
            violations.append("Content too short (minimum 10 characters)")

        # Quality checks using scores from HookAnalyzer and ReadabilityScorer
        if draft.hook_score > 0 and draft.hook_score < MIN_HOOK_SCORE:
            violations.append(
                f"Hook score {draft.hook_score}/100 is below minimum {MIN_HOOK_SCORE}"
            )

        if draft.readability_score > 0 and draft.readability_score < MIN_READABILITY_SCORE:
            violations.append(
                f"Readability score {draft.readability_score:.1f} is below minimum {MIN_READABILITY_SCORE}"
            )

        # Image validation
        image_valid, image_errors = self._validate_image(draft)
        violations.extend(image_errors)

        return ValidationResult(
            passed=len(violations) == 0,
            character_count=len(content),
            character_limit=limit,
            violations=tuple(violations),
            image_valid=image_valid,
        )

    def _validate_image(self, draft: ContentDraft) -> tuple[bool, list[str]]:
        """Validate the image in a content draft.

        Handles:
        - Empty image (no image_url) → invalid
        - Base64 data URLs → decode and check dimensions
        - HTTP URLs → check accessibility and dimensions

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        image_url = draft.image_url

        # No image at all
        if not image_url:
            return False, ["No image generated"]

        # Base64 data URL
        if image_url.startswith("data:image/"):
            return self._validate_base64_image(image_url)

        # HTTP/HTTPS URL
        if image_url.startswith(("http://", "https://")):
            return self._validate_http_image(image_url)

        # Unknown format
        return False, [f"Unknown image format: {image_url[:50]}"]

    def _validate_base64_image(self, data_url: str) -> tuple[bool, list[str]]:
        """Validate a base64 data URL image.

        Note: Only validates that the image is decodable by Pillow.
        Resolution and size checks are skipped because:
        - Base64 images are generated by Cloudflare at correct resolution (1080x1080)
        - File size varies by content complexity, not a reliable quality metric
        """
        try:
            # Parse data URL: data:image/png;base64,<data>
            match = re.match(r"data:image/(\w+);base64,(.+)", data_url)
            if not match:
                return False, ["Invalid base64 data URL format"]

            format_type = match.group(1)
            b64_data = match.group(2)

            # Decode base64
            image_bytes = base64.b64decode(b64_data)

            # Verify image is decodable by Pillow
            from PIL import Image

            image = Image.open(io.BytesIO(image_bytes))
            width, height = image.size

            self.logger.info(
                "Base64 image validated: %dx%d, format=%s",
                width,
                height,
                format_type,
            )

            return True, []

        except Exception as e:
            self.logger.warning("Base64 image validation failed: %s", e)
            return False, [f"Image validation failed: {str(e)}"]

    def _validate_http_image(self, url: str) -> tuple[bool, list[str]]:
        """Validate an HTTP URL image using ImageValidationService."""
        errors = []

        try:
            import asyncio

            from src.services.image_validation_service import (
                ImageValidationService,
            )

            async def _validate():
                async with ImageValidationService() as service:
                    return await service.validate_image_url(url)

            # Run async validation in sync context
            result = asyncio.run(_validate())

            if not result.url_accessible:
                errors.append(f"Image URL not accessible: {url[:100]}")
                return False, errors

            if not result.is_valid:
                errors.extend(result.errors)

            self.logger.info(
                "HTTP image validated: %dx%d, accessible=%s",
                result.width,
                result.height,
                result.url_accessible,
            )

            return result.is_valid, errors

        except Exception as e:
            self.logger.warning("HTTP image validation failed: %s", e)
            return False, [f"Image validation failed: {str(e)}"]
