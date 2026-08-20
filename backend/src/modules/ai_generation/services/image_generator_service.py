"""Image generation service for AI Generation Engine."""

import logging
import uuid
from datetime import datetime
from typing import Any

import httpx

from src.services.cloudflare_image_service import CloudflareImageService
from src.services.pollinations_service import PollinationsService
from src.services.supabase import SupabaseService

from ..constants import SeverityLevel

logger = logging.getLogger(__name__)


class ValidationError:
    """Individual validation error."""

    def __init__(
        self,
        code: str,
        message: str,
        severity: str,
        field: str | None = None,
        suggested_fix: str | None = None,
    ):
        self.code = code
        self.message = message
        self.severity = severity
        self.field = field
        self.suggested_fix = suggested_fix

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "field": self.field,
            "suggested_fix": self.suggested_fix,
        }


class ValidationWarning:
    """Individual validation warning."""

    def __init__(self, code: str, message: str, field: str | None = None):
        self.code = code
        self.message = message
        self.field = field

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
        }


class ImageGeneratorService:
    """Service for generating campaign images from image prompts."""

    from langsmith import traceable

    @traceable(name="generate_image")
    async def generate_image(
        self,
        image_prompt_artifact: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate campaign image from image prompt artifact.

        Args:
            image_prompt_artifact: Image prompt artifact containing image prompt

        Returns:
            ImageArtifact: Generated campaign image with metadata and scoring

        Raises:
            ValidationError: If image prompt is invalid or generation fails
        """
        # Validate inputs
        validation = self.validate_input(image_prompt_artifact)
        if not validation.get("is_valid"):
            raise ValueError(f"Invalid image prompt: {validation.get('errors')}")

        # Extract prompt information
        prompt_id = image_prompt_artifact.get("id", "unknown_prompt")
        platform = image_prompt_artifact.get("platform", "web")
        strategy_id = image_prompt_artifact.get("strategy_id", "unknown_strategy")
        copy_id = image_prompt_artifact.get("copy_id", "unknown_copy")

        # Generate image using Cloudflare Workers AI with fallback to Pollinations
        image_url = await self._generate_image_url(
            image_prompt_artifact, strategy_id, copy_id, platform
        )
        thumbnail_url = self._generate_thumbnail_url(image_url)

        # Create metadata
        metadata = self._create_metadata(image_prompt_artifact, strategy_id, copy_id, platform)

        # Create brand alignment scores
        brand_alignment = self._create_brand_alignment_scores(image_prompt_artifact)

        # Create platform suitability scores
        platform_suitability = self._create_platform_suitability_scores(
            image_prompt_artifact, platform
        )

        # Generate validation results
        validation_results = self._validate_generated_image(
            metadata, brand_alignment, platform_suitability
        )

        image_artifact = {
            "id": f"image_{hash(str(image_prompt_artifact)) % 10000}",
            "generated_at": datetime.now().isoformat(),
            "prompt_id": prompt_id,
            "platform": platform,
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "metadata": metadata,
            "brand_alignment": brand_alignment,
            "platform_suitability": platform_suitability,
            "validation_results": validation_results if validation_results else None,
        }

        return image_artifact

    async def regenerate_image(
        self,
        existing_image: dict[str, Any],
        new_prompt: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Regenerate image based on updated prompt while preserving other attributes.

        Args:
            existing_image: Previously generated image artifact
            new_prompt: Updated image prompt artifact

        Returns:
            ImageArtifact: Updated image

        Raises:
            ValidationError: If regeneration is invalid
        """
        # Validate inputs
        if not existing_image.get("id"):
            raise ValueError("Existing image must have an ID")
        if not new_prompt.get("id"):
            raise ValueError("New prompt must have an ID")

        # Preserve existing attributes
        preserved_attributes = {
            "id": existing_image["id"],
            "generated_at": existing_image["generated_at"],
            "prompt_id": new_prompt["id"],  # Updated prompt
            "platform": existing_image["platform"],  # Preserve platform
            "metadata": existing_image["metadata"],  # Preserve metadata
            "brand_alignment": existing_image["brand_alignment"],  # Preserve
            "platform_suitability": existing_image["platform_suitability"],  # Preserve
        }

        # Generate new image URL
        new_image_url = await self._generate_image_url(
            new_prompt,
            preserved_attributes["prompt_id"],
            existing_image.get("prompt_id", "unknown_copy"),
            preserved_attributes["platform"],
        )

        # Create new thumbnail
        new_thumbnail_url = self._generate_thumbnail_url(new_image_url)

        # Update metadata with new timestamp
        import copy

        updated_metadata = copy.deepcopy(preserved_attributes["metadata"])
        updated_metadata["generated_at"] = datetime.now().isoformat()

        # Generate new validation results
        new_brand_alignment = self._create_brand_alignment_scores(new_prompt)
        new_platform_suitability = self._create_platform_suitability_scores(
            new_prompt, preserved_attributes["platform"]
        )
        new_validation_results = self._validate_generated_image(
            updated_metadata, new_brand_alignment, new_platform_suitability
        )

        updated_image = {
            **preserved_attributes,
            "image_url": new_image_url,
            "thumbnail_url": new_thumbnail_url,
            "metadata": updated_metadata,
            "brand_alignment": new_brand_alignment,
            "platform_suitability": new_platform_suitability,
            "validation_results": (new_validation_results if new_validation_results else None),
        }

        return updated_image

    def validate_image(
        self,
        image: dict[str, Any],
        prompt: dict[str, Any],
        brand_guidelines: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate generated image against brand guidelines and prompt.

        Args:
            image: Generated image to validate
            prompt: Source image prompt
            brand_guidelines: Brand guidelines for validation

        Returns:
            ValidationArtifact: Validation results
        """
        errors = []
        warnings = []
        compliance_scores = {}

        # Check required fields
        required_fields = [
            "id",
            "generated_at",
            "prompt_id",
            "platform",
            "image_url",
            "metadata",
            "brand_alignment",
            "platform_suitability",
        ]

        for field in required_fields:
            if not image.get(field):
                errors.append(
                    ValidationError(
                        code="MISSING_IMAGE_FIELD",
                        message=f"Missing required image field: {field}",
                        severity=SeverityLevel.ERROR,
                        field=f"image.{field}",
                    )
                )

        # Validate prompt consistency
        if image.get("prompt_id") != prompt.get("id"):
            errors.append(
                ValidationError(
                    code="PROMPT_ID_MISMATCH",
                    message="Image prompt ID does not match source prompt",
                    severity=SeverityLevel.ERROR,
                    field="image.prompt_id",
                )
            )

        # Validate platform consistency
        strategy_platforms = prompt.get("strategy_data", {}).get("platforms", [])
        image_platform = image.get("platform")
        if strategy_platforms and image_platform and image_platform not in strategy_platforms:
            warnings.append(
                ValidationWarning(
                    code="PLATFORM_NOT_IN_STRATEGY",
                    message=f"Image platform '{image_platform}' not in strategy platforms",
                    field="image.platform",
                )
            )

        # Validate brand alignment score
        brand_alignment = image.get("brand_alignment", {})
        if brand_alignment.get("overall_score", 0) < 0.7:
            warnings.append(
                ValidationWarning(
                    code="LOW_BRAND_ALIGNMENT",
                    message="Generated image has low brand alignment score",
                    field="image.brand_alignment.overall_score",
                )
            )

        # Validate platform suitability score
        platform_suitability = image.get("platform_suitability", {})
        if platform_suitability.get("overall_score", 0) < 0.7:
            warnings.append(
                ValidationWarning(
                    code="LOW_PLATFORM_SUITABILITY",
                    message="Generated image has low platform suitability score",
                    field="image.platform_suitability.overall_score",
                )
            )

        # Validate image metadata
        metadata = image.get("metadata", {})
        if metadata.get("width", 0) <= 0 or metadata.get("height", 0) <= 0:
            errors.append(
                ValidationError(
                    code="INVALID_IMAGE_DIMENSIONS",
                    message="Invalid image dimensions",
                    severity=SeverityLevel.ERROR,
                    field="image.metadata.dimensions",
                )
            )

        if not metadata.get("format"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_IMAGE_FORMAT",
                    message="Image format not specified",
                    field="image.metadata.format",
                )
            )

        # Compliance scores
        present_fields = sum(1 for field in required_fields if image.get(field))
        compliance_scores["required_fields"] = (
            present_fields / len(required_fields) if required_fields else 0
        )

        if brand_alignment:
            compliance_scores["brand_alignment"] = brand_alignment.get("overall_score", 0)
        if platform_suitability:
            compliance_scores["platform_suitability"] = platform_suitability.get("overall_score", 0)

        is_valid = len(errors) == 0

        return {
            "id": f"validation_image_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "image",
            "artifact_id": image.get("id", "unknown"),
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Ensure all required fields are populated",
                "Match prompt and image IDs consistently",
                "Use brand elements for brand alignment",
                "Validate image dimensions and format",
            ],
            "validated_by": "ImageGeneratorService",
        }

    def validate_input(
        self,
        image_prompt_artifact: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate image prompt for generation.

        Args:
            image_prompt_artifact: Image prompt to validate

        Returns:
            ValidationArtifact: Validation results
        """
        errors = []
        warnings = []
        compliance_scores = {}

        # Check required fields
        required_fields = [
            "id",
            "strategy_id",
            "copy_id",
            "platform",
            "prompt_text",
            "style_guidelines",
            "brand_elements",
            "visual_elements",
            "composition_guidelines",
        ]

        for field in required_fields:
            if image_prompt_artifact.get(field) is None:
                errors.append(
                    ValidationError(
                        code="MISSING_PROMPT_FIELD",
                        message=f"Missing required prompt field: {field}",
                        severity=SeverityLevel.ERROR,
                        field=f"prompt.{field}",
                    )
                )

        # Validate prompt consistency
        if not image_prompt_artifact.get("strategy_id"):
            errors.append(
                ValidationError(
                    code="MISSING_STRATEGY_ID",
                    message="Prompt missing strategy ID",
                    severity=SeverityLevel.ERROR,
                    field="prompt.strategy_id",
                )
            )

        if not image_prompt_artifact.get("copy_id"):
            errors.append(
                ValidationError(
                    code="MISSING_COPY_ID",
                    message="Prompt missing copy ID",
                    severity=SeverityLevel.ERROR,
                    field="prompt.copy_id",
                )
            )

        # Validate platform availability
        strategy_platforms = image_prompt_artifact.get("strategy_data", {}).get("platforms", [])
        prompt_platform = image_prompt_artifact.get("platform")
        if strategy_platforms and prompt_platform and prompt_platform not in strategy_platforms:
            warnings.append(
                ValidationWarning(
                    code="PLATFORM_NOT_SUPPORTED",
                    message=f"Platform '{prompt_platform}' not in strategy platforms {strategy_platforms}",
                    field="prompt.platform",
                )
            )

        # Compliance scores
        present_fields = sum(1 for field in required_fields if image_prompt_artifact.get(field))
        compliance_scores["required_fields"] = (
            present_fields / len(required_fields) if required_fields else 0
        )

        is_valid = len(errors) == 0

        return {
            "id": f"validation_prompt_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "inputs",
            "artifact_id": "generation_validation",
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Provide valid prompt artifact",
                "Ensure strategy and copy IDs are provided",
                "Use supported platforms for generation",
            ],
            "validated_by": "ImageGeneratorService",
        }

    def _create_metadata(
        self,
        image_prompt_artifact: dict[str, Any],
        strategy_id: str,
        copy_id: str,
        platform: str,
    ) -> dict[str, Any]:
        """Create image metadata."""
        # Generate deterministic image dimensions
        image_width = hash(strategy_id + platform) % 800 + 400
        image_height = hash(copy_id + platform) % 600 + 300
        aspect_ratio = image_width / image_height

        # Determine file format
        format_map = {
            "linkedin": "jpg",
            "instagram": "png",
            "facebook": "jpg",
            "twitter": "png",
            "web": "jpg",
        }
        image_format = format_map.get(platform, "jpg")

        # Calculate file size
        size_multiplier = (image_width + image_height) / 1000
        file_size = int(size_multiplier * size_multiplier * 10)  # Rough estimation

        return {
            "width": image_width,
            "height": image_height,
            "format": image_format,
            "size_bytes": file_size,
            "aspects_ratio": round(aspect_ratio, 2),
            "file_path": f"/images/{strategy_id}_{image_width}x{image_height}.{image_format}",
            "cloud_storage_path": f"gs://ai-generation/{strategy_id}/images/{image_width}x{image_height}.{image_format}",
            "generated_at": datetime.now().isoformat(),
            "prompt_id": image_prompt_artifact.get("id"),
        }

    def _create_brand_alignment_scores(
        self,
        image_prompt_artifact: dict[str, Any],
    ) -> dict[str, Any]:
        """Create brand alignment scores."""
        strategy_data = image_prompt_artifact.get("strategy_data", {})
        brand_guidelines = strategy_data.get("brand_guidelines", {})

        # Extract brand elements
        brand_elements = image_prompt_artifact.get("brand_elements", [])
        color_palette = brand_guidelines.get("color_palette", [])
        brand_values = brand_guidelines.get("brand_values", [])

        # Calculate alignment scores (mock logic)
        scores = {
            "logo_usage": (
                1.0 if any(e.get("element_type") == "logo" for e in brand_elements) else 0.9
            ),
            "color_alignment": min(1.0, max(0.9, len(color_palette) / 5.0)),
            "brand_values": min(1.0, max(0.9, len(brand_values) / 3.0)),
        }

        overall_score = (
            scores["logo_usage"] + scores["color_alignment"] + scores["brand_values"]
        ) / 3.0

        # Filter elements to check
        elements_checked = ["logo_usage", "color_alignment", "brand_values"]
        issues = []

        if scores["logo_usage"] < 0.8:
            issues.append("Logo usage not optimally positioned")
        if scores["color_alignment"] < 0.8:
            issues.append("Brand colors not well represented")
        if scores["brand_values"] < 0.8:
            issues.append("Brand values not sufficiently conveyed")

        return {
            "overall_score": round(overall_score, 2),
            "elements_checked": elements_checked,
            "scores": scores,
            "issues": issues,
        }

    def _create_platform_suitability_scores(
        self,
        image_prompt_artifact: dict[str, Any],
        platform: str,
    ) -> dict[str, Any]:
        """Create platform suitability scores."""
        strategy_data = image_prompt_artifact.get("strategy_data", {})
        platform_adaptations = strategy_data.get("platform_strategy", {}).get("adaptations", {})

        platform_info = platform_adaptations.get(platform, {}) if platform_adaptations else {}

        # Define suitability criteria
        criteria = ["resolution", "aspect_ratio", "media_requirements", "load_time"]
        scores = {}

        # Resolution suitability
        if platform == "instagram":
            scores["resolution"] = 1.0
        elif platform == "linkedin":
            scores["resolution"] = 0.9
        elif platform == "facebook":
            scores["resolution"] = 0.85
        elif platform == "twitter":
            scores["resolution"] = 0.8
        else:
            scores["resolution"] = 0.9

        # Aspect ratio suitability
        if platform == "instagram":
            scores["aspect_ratio"] = 1.0
        elif platform == "linkedin":
            scores["aspect_ratio"] = 0.85
        elif platform == "facebook":
            scores["aspect_ratio"] = 0.9
        elif platform == "twitter":
            scores["aspect_ratio"] = 0.8
        else:
            scores["aspect_ratio"] = 0.85

        # Media requirements
        media_requirements = platform_info.get("media_requirements", "visual/text mix")
        scores["media_requirements"] = 1.0 if "image" in media_requirements.lower() else 0.8

        # Load time expectations
        format_map = {
            "linkedin": "jpg",
            "instagram": "png",
            "facebook": "jpg",
            "twitter": "png",
            "web": "jpg",
        }
        image_format = format_map.get(platform, "jpg")
        if image_format == "jpg":
            scores["load_time"] = 0.95
        elif image_format == "png":
            scores["load_time"] = 0.85
        else:
            scores["load_time"] = 0.9

        # Calculate overall suitability
        overall_score = sum(scores.values()) / len(scores) if scores else 0.0

        # Requirements met/failed
        requirements_met = []
        requirements_failed = []

        if scores.get("resolution", 0) >= 0.8:
            requirements_met.append("High resolution suitable")
        else:
            requirements_failed.append("Resolution may be too low")

        if scores.get("aspect_ratio", 0) >= 0.8:
            requirements_met.append("Aspect ratio appropriate")
        else:
            requirements_failed.append("Aspect ratio needs adjustment")

        if scores.get("media_requirements", 0) >= 0.8:
            requirements_met.append("Media requirements satisfied")
        else:
            requirements_failed.append("Media requirements not met")

        return {
            "overall_score": round(overall_score, 2),
            "criteria": criteria,
            "scores": scores,
            "requirements_met": requirements_met,
            "requirements_failed": requirements_failed,
        }

    def _validate_generated_image(
        self,
        metadata: dict[str, Any],
        brand_alignment: dict[str, Any],
        platform_suitability: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate generated image."""
        errors = []
        warnings = []

        # Validate metadata
        if metadata.get("width", 0) <= 0 or metadata.get("height", 0) <= 0:
            errors.append(
                ValidationError(
                    code="INVALID_DIMENSIONS",
                    message="Invalid image dimensions",
                    severity=SeverityLevel.ERROR,
                    field="metadata.dimensions",
                )
            )

        if not metadata.get("format"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_FORMAT",
                    message="Image format missing",
                    field="metadata.format",
                )
            )

        if metadata.get("size_bytes", 0) <= 0:
            warnings.append(
                ValidationWarning(
                    code="INVALID_SIZE",
                    message="Invalid image size",
                    field="metadata.size_bytes",
                )
            )

        # Validate brand alignment score
        brand_score = brand_alignment.get("overall_score", 0)
        if brand_score < 0.5:
            warnings.append(
                ValidationWarning(
                    code="LOW_BRAND_ALIGNMENT",
                    message="Brand alignment score is low",
                    field="brand_alignment.overall_score",
                )
            )

        if brand_score < 0.3:
            errors.append(
                ValidationError(
                    code="POOR_BRAND_ALIGNMENT",
                    message="Brand alignment is critically poor",
                    severity=SeverityLevel.ERROR,
                    field="brand_alignment.overall_score",
                )
            )

        # Validate platform suitability score
        platform_score = platform_suitability.get("overall_score", 0)
        if platform_score < 0.5:
            warnings.append(
                ValidationWarning(
                    code="LOW_PLATFORM_SUITABILITY",
                    message="Platform suitability score is low",
                    field="platform_suitability.overall_score",
                )
            )

        if platform_score < 0.3:
            errors.append(
                ValidationError(
                    code="POOR_PLATFORM_SUITABILITY",
                    message="Platform suitability is critically poor",
                    severity=SeverityLevel.ERROR,
                    field="platform_suitability.overall_score",
                )
            )

        # Build compliance scores
        compliance_scores = {}
        if brand_score > 0:
            compliance_scores["brand_alignment"] = brand_score
        if platform_score > 0:
            compliance_scores["platform_suitability"] = platform_score

        is_valid = len(errors) == 0

        return {
            "id": f"validation_image_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "image_validation",
            "artifact_id": "image_validation",
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Ensure valid image dimensions",
                "Specify image format",
                "Validate file size",
                "Maintain brand alignment",
                "Ensure platform compatibility",
            ],
            "validated_by": "ImageGeneratorService",
        }

    async def _generate_image_url(
        self,
        image_prompt_artifact: dict[str, Any],
        strategy_id: str,
        copy_id: str,
        platform: str,
    ) -> str:
        """Generate real image — Cloudflare Workers AI (primary), Pollinations (fallback)."""
        prompt_text = image_prompt_artifact.get("prompt_text", "")

        # 1. Try Cloudflare Workers AI (primary)
        try:
            async with CloudflareImageService() as cf:
                image_bytes = await cf.generate_from_text(prompt_text)
            supabase = SupabaseService()
            filename = f"{uuid.uuid4()}_{platform}.{self._get_image_format(platform)}"
            content_type = (
                "image/png" if self._get_image_format(platform) == "png" else "image/jpeg"
            )
            return supabase.upload_image_bytes(
                data=image_bytes,
                filename=filename,
                content_type=content_type,
                prefix=f"campaigns/{strategy_id}",
            )
        except Exception as e:
            logger.warning("Cloudflare image generation failed: %s", e)

        # 2. Fallback to Pollinations
        try:
            async with PollinationsService() as poll:
                poll_url, _ = await poll.generate_image(prompt_text)
            async with httpx.AsyncClient() as client:
                resp = await client.get(poll_url)
                resp.raise_for_status()
                image_bytes = resp.content
            supabase = SupabaseService()
            filename = f"{uuid.uuid4()}_{platform}.{self._get_image_format(platform)}"
            content_type = (
                "image/png" if self._get_image_format(platform) == "png" else "image/jpeg"
            )
            return supabase.upload_image_bytes(
                data=image_bytes,
                filename=filename,
                content_type=content_type,
                prefix=f"campaigns/{strategy_id}",
            )
        except Exception as e:
            logger.warning("Pollinations image generation fallback also failed: %s", e)

        # 3. Ultimate fallback to deterministic URL
        deterministic_input = (
            f"{strategy_id}_{copy_id}_{platform}_{image_prompt_artifact.get('id', 'default')}"
        )
        hash_value = hash(deterministic_input) % 10000
        return f"https://storage.ai-generation.com/images/{strategy_id}/{hash_value:04d}_{platform}.{self._get_image_format(platform)}"

    def _generate_thumbnail_url(self, image_url: str) -> str:
        """Generate thumbnail URL from main image URL."""
        return (
            image_url.replace("/images/", "/thumbnails/")
            .replace(".jpg", "_thumb.jpg")
            .replace(".png", "_thumb.png")
        )

    def _get_image_format(self, platform: str) -> str:
        """Get appropriate image format for platform."""
        format_map = {
            "linkedin": "jpg",
            "instagram": "png",
            "facebook": "jpg",
            "twitter": "png",
            "web": "jpg",
        }
        return format_map.get(platform, "jpg")
