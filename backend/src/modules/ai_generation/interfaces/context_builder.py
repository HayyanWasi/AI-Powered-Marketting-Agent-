from typing import Any

from ..models.generation_context import GenerationContext
from ..models.validation_artifact import ValidationArtifact


class ContextBuilderInterface:
    """Interface for building generation context from campaign inputs."""

    def build_generation_context(
        self,
        campaign_context: dict[str, Any],
        company_profile: dict[str, Any],
        audience: dict[str, Any],
        platforms: list[str],
        brand_guidelines: dict[str, Any],
        reference_materials: list[dict[str, Any]],
        user_intent: dict[str, Any] | None = None,
    ) -> GenerationContext:
        """
        Build a complete generation context from input artifacts.

        Args:
            campaign_context: Campaign parameters including goals, audience segments, budget, timeline
            company_profile: Company brand information, voice, values, positioning
            audience: Target audience demographics, interests, pain points, buying behavior
            platforms: List of target platforms (e.g., LinkedIn, Instagram, Twitter)
            brand_guidelines: Brand voice tone, style guidelines, logo specifications, color palette
            reference_materials: Relevant assets, benchmarks, competitor examples, previous campaigns
            user_intent: Additional instructions for specific content variations or emphasis (optional)

        Returns:
            GenerationContext: Complete generation context

        Raises:
            ValidationError: If input validation fails
        """
        ...

    def validate_context_completeness(
        self,
        context: dict[str, Any],
    ) -> ValidationArtifact:
        """
        Validate that a generation context contains all required fields.

        Args:
            context: Context to validate

        Returns:
            ValidationArtifact: Validation results
        """
        ...
