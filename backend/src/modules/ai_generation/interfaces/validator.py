"""Validator interface for AI Generation Engine."""

from typing import Dict, Any, List

from ..models.validation_artifact import ValidationArtifact


class ValidatorInterface:
    """Interface for validating all generated artifacts against business rules."""

    def validate_all_artifacts(
        self,
        artifacts: Dict[str, Any],
    ) -> ValidationArtifact:
        """
        Validate all generated artifacts against business rules and platform requirements.

        Args:
            artifacts: Dictionary containing all artifacts to validate
                      (strategy, copy, image prompts, images)

        Returns:
            ValidationArtifact: Comprehensive validation results

        Raises:
            ValidationError: If validation fails or is malformed
        """
        ...

    def validate_artifact(
        self,
        artifact: Dict[str, Any],
        artifact_type: str,
    ) -> ValidationArtifact:
        """
        Validate a specific artifact type against appropriate rules.

        Args:
            artifact: Artifact to validate
            artifact_type: Type of artifact (strategy, copy, image_prompt, image)

        Returns:
            ValidationArtifact: Validation results
        """
        ...

    def get_business_rules(
        self,
        artifact_type: str,
    ) -> Dict[str, Any]:
        """
        Get business rules for validating a specific artifact type.

        Args:
            artifact_type: Type of artifact (strategy, copy, image_prompt, image)

        Returns:
            Dict[str, Any]: Business rules for validation
        """
        ...

    def get_platform_requirements(
        self,
        platform: str,
    ) -> Dict[str, Any]:
        """
        Get platform-specific validation requirements.

        Args:
            platform: Target platform

        Returns:
            Dict[str, Any]: Platform requirements
        """
        ...
