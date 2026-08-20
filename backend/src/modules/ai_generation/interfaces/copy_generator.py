"""Copy generator interface for AI Generation Engine."""

from typing import Any

from ..models.copy_artifact import CopyArtifact
from ..models.validation_artifact import ValidationArtifact


class CopyGeneratorInterface:
    """Interface for generating platform-specific copy from strategy artifact."""

    def generate_copy(
        self,
        strategy_artifact: dict[str, Any],
        platform: str,
    ) -> CopyArtifact:
        """
        Generate platform-specific copy from strategy.

        Args:
            strategy_artifact: Strategy artifact containing approved campaign strategy
            platform: Target platform for copy generation

        Returns:
            CopyArtifact: Generated marketing copy

        Raises:
            ValidationError: If strategy is invalid or platform unsupported
        """
        ...

    def regenerate_copy(
        self,
        existing_copy: dict[str, Any],
        new_context: dict[str, Any],
    ) -> CopyArtifact:
        """
        Regenerate copy based on updated context while preserving strategy.

        Args:
            existing_copy: Previously generated copy artifact
            new_context: Updated context with regeneration instructions

        Returns:
            CopyArtifact: Updated copy

        Raises:
            ValidationError: If regeneration context is invalid
        """
        ...

    def validate_copy(
        self,
        copy: dict[str, Any],
        platform: str,
    ) -> ValidationArtifact:
        """
        Validate generated copy against platform requirements.

        Args:
            copy: Copy to validate
            platform: Target platform

        Returns:
            ValidationArtifact: Validation results
        """
        ...
