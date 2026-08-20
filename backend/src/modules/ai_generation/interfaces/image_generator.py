"""Image generator interface for AI Generation Engine."""

from typing import Any

from ..models.image_artifact import ImageArtifact
from ..models.validation_artifact import ValidationArtifact


class ImageGeneratorInterface:
    """Interface for generating campaign images from image prompts."""

    def generate_image(
        self,
        image_prompt_artifact: dict[str, Any],
    ) -> ImageArtifact:
        """
        Generate campaign image from image prompt artifact.

        Args:
            image_prompt_artifact: Image prompt artifact containing image prompt

        Returns:
            ImageArtifact: Generated campaign image with metadata and scoring

        Raises:
            ValidationError: If image prompt is invalid or generation fails
        """
        ...

    def regenerate_image(
        self,
        existing_image: dict[str, Any],
        new_prompt: dict[str, Any],
    ) -> ImageArtifact:
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
        ...

    def validate_image(
        self,
        image: dict[str, Any],
        prompt: dict[str, Any],
        brand_guidelines: dict[str, Any],
    ) -> ValidationArtifact:
        """
        Validate generated image against brand guidelines and prompt.

        Args:
            image: Generated image to validate
            prompt: Source image prompt
            brand_guidelines: Brand guidelines for validation

        Returns:
            ValidationArtifact: Validation results
        """
        ...
