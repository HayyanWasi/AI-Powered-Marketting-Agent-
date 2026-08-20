"""Image prompt editor interface for AI Generation Engine."""

from typing import Any

from ..models.image_prompt_artifact import ImagePromptArtifact
from ..models.validation_artifact import ValidationArtifact


class ImagePromptEditorInterface:
    """Interface for editing image prompts from strategy and copy artifacts."""

    def generate_image_prompt(
        self,
        strategy_artifact: dict[str, Any],
        copy_artifact: dict[str, Any],
        platform: str,
    ) -> ImagePromptArtifact:
        """
        Generate image prompt from strategy and copy artifacts.

        Args:
            strategy_artifact: Strategy artifact containing campaign strategy
            copy_artifact: Copy artifact containing approved marketing copy
            platform: Target platform for image generation

        Returns:
            ImagePromptArtifact: Structured image prompt

        Raises:
            ValidationError: If input artifacts are invalid or incompatible
        """
        ...

    def validate_image_prompt(
        self,
        prompt: dict[str, Any],
        strategy: dict[str, Any],
        copy: dict[str, Any],
    ) -> ValidationArtifact:
        """
        Validate image prompt against strategy and copy.

        Args:
            prompt: Image prompt to validate
            strategy: Source strategy artifact
            copy: Source copy artifact

        Returns:
            ValidationArtifact: Validation results
        """
        ...
