"""Context builder service for AI Generation Engine."""

from datetime import datetime
from typing import Any

from ..models.generation_context import GenerationContext
from ..models.validation_artifact import (
    SeverityLevel,
    ValidationArtifact,
    ValidationError,
    ValidationWarning,
)


class ContextBuilderService:
    """Service for building generation context from campaign inputs."""

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
        validation = self.validate_context_completeness(
            {
                "campaign_context": campaign_context,
                "company_profile": company_profile,
                "audience": audience,
                "platforms": platforms,
                "brand_guidelines": brand_guidelines,
                "reference_materials": reference_materials,
                "user_intent": user_intent,
            }
        )

        if not validation.is_success():
            raise ValueError(f"Invalid generation context: {validation.errors}")

        context = GenerationContext(
            campaign_context=campaign_context,
            company_profile=company_profile,
            audience=audience,
            platforms=platforms,
            brand_guidelines=brand_guidelines,
            reference_materials=reference_materials,
            user_intent=user_intent,
        )

        return context

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
        errors = []
        warnings = []
        compliance_scores = {}

        # Required fields
        required_fields = [
            "campaign_context",
            "company_profile",
            "audience",
            "platforms",
            "brand_guidelines",
            "reference_materials",
        ]

        for field in required_fields:
            if field not in context or not context[field]:
                errors.append(
                    ValidationError(
                        code="MISSING_REQUIRED_FIELD",
                        message=f"Missing required field: {field}",
                        severity=SeverityLevel.ERROR,
                        field=field,
                        suggested_fix=f"Provide the required field: {field}",
                    )
                )

        # Check campaign context completeness
        campaign_context = context.get("campaign_context", {})
        if not campaign_context.get("name"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_CAMPAIGN_NAME",
                    message="Campaign name is recommended for better context",
                    field="campaign_context.name",
                )
            )

        # Check brand guidelines completeness
        brand_guidelines = context.get("brand_guidelines", {})
        if not brand_guidelines.get("voice_tone"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_BRAND_VOICE",
                    message="Brand voice tone is recommended for consistent content generation",
                    field="brand_guidelines.voice_tone",
                )
            )

        # Check platform requirements
        platforms = context.get("platforms", [])
        if not platforms:
            warnings.append(
                ValidationWarning(
                    code="EMPTY_PLATFORMS",
                    message="No platforms specified - copy will not be generated for specific platforms",
                    field="platforms",
                )
            )

        # Compliance scores
        total_fields = len(required_fields)
        present_fields = sum(1 for field in required_fields if field in context and context[field])
        compliance_scores["required_fields"] = (
            present_fields / total_fields if total_fields > 0 else 0
        )

        is_valid = len(errors) == 0

        return ValidationArtifact(
            id=f"validation_{datetime.now().isoformat()}",
            generated_at=datetime.now(),
            artifact_type="generation_context",
            artifact_id="context_validation",
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            compliance_scores=compliance_scores,
            recommendations=[
                "Ensure all required fields are provided for complete context",
                "Add brand guidelines for consistent content generation",
                "Specify target platforms for platform-specific content",
            ],
            validated_by="ContextBuilderService",
        )
