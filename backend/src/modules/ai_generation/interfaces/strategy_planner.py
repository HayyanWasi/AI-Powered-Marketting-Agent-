"""Strategy planner interface for AI Generation Engine."""

from typing import Dict, Any, Optional

from ..models.strategy_artifact import StrategyArtifact
from ..models.validation_artifact import ValidationArtifact


class StrategyPlannerInterface:
    """Interface for planning campaign strategy from generation context."""

    def generate_strategy(
        self,
        generation_context: Dict[str, Any],
    ) -> StrategyArtifact:
        """
        Generate campaign strategy from generation context.

        Args:
            generation_context: Complete generation context containing campaign, company,
                               audience, platforms, brand guidelines, and reference materials

        Returns:
            StrategyArtifact: Structured campaign strategy

        Raises:
            ValidationError: If generation context is invalid or incomplete
        """
        ...

    def validate_strategy(
        self,
        strategy: Dict[str, Any],
    ) -> ValidationArtifact:
        """
        Validate generated strategy against business rules.

        Args:
            strategy: Strategy to validate

        Returns:
            ValidationArtifact: Validation results
        """
        ...
