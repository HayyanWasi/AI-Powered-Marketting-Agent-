"""LLM service for AI Generation Engine."""

import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..constants import SeverityLevel


class ValidationError:
    """Individual validation error."""

    def __init__(
        self,
        code: str,
        message: str,
        severity: str,
        field: Optional[str] = None,
        suggested_fix: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.severity = severity
        self.field = field
        self.suggested_fix = suggested_fix

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "field": self.field,
            "suggested_fix": self.suggested_fix,
        }


class ValidationWarning:
    """Individual validation warning."""

    def __init__(self, code: str, message: str, field: Optional[str] = None):
        self.code = code
        self.message = message
        self.field = field

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
        }


class LLMService:
    """Service for LLM-powered text generation."""

    def generate_strategy(
        self,
        generation_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate campaign strategy using LLM.

        Args:
            generation_context: Complete generation context

        Returns:
            StrategyArtifact: Generated strategy
        """
        # Mock implementation for deterministic testing
        context = generation_context

        # Simulate deterministic LLM response based on input
        strategy_text = f"Strategy for {context['campaign_context'].get('name', 'Campaign')} targeting {context['audience'].get('segments', ['target'])} on {', '.join(context['platforms'])}"

        audience_strategy = {
            "target_segments": context["audience"].get("segments", []),
            "messaging_approach": "Professional and engaging",
            "key_messages": ["Value proposition", "Differentiation", "Call to action"],
        }

        messaging_strategy = {
            "tone": context["brand_guidelines"].get("voice_tone", "professional"),
            "style": "Clear and concise",
            "key_points": ["Problem", "Solution", "Benefits"],
        }

        platform_strategy = {
            "platforms": context["platforms"],
            "adaptations": {
                platform: {
                    "format": "Standard",
                    "length_constraints": "Platform-specific",
                    "media_requirements": "Visual/text mix",
                }
                for platform in context["platforms"]
            },
        }

        seo_strategy = {
            "keywords": ["campaign", "marketing", "strategy"],
            "optimization_targets": ["awareness", "conversion"],
        }

        campaign_strategy = {
            "goals": context["campaign_context"].get(
                "goals", ["brand awareness", "lead generation"]
            ),
            "timeline": context["campaign_context"].get("timeline", "Q4 2026"),
            "budget_constraints": context["campaign_context"].get("budget", "unknown"),
        }

        strategy = {
            "id": f"strategy_{random.randint(1000, 9999)}",
            "generated_at": datetime.now().isoformat(),
            "audience_strategy": audience_strategy,
            "messaging_strategy": messaging_strategy,
            "platform_strategy": platform_strategy,
            "seo_strategy": seo_strategy,
            "campaign_strategy": campaign_strategy,
            "validation_results": None,
        }

        return strategy

    def validate_strategy_content(
        self,
        strategy: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate strategy content for consistency.

        Args:
            strategy: Strategy to validate

        Returns:
            ValidationArtifact: Validation results
        """
        errors = []
        warnings = []
        compliance_scores = {}

        # Check if strategy has all required components
        required_components = [
            "audience_strategy",
            "messaging_strategy",
            "platform_strategy",
            "seo_strategy",
            "campaign_strategy",
        ]

        for component in required_components:
            if not strategy.get(component):
                errors.append(
                    ValidationError(
                        code="MISSING_STRATEGY_COMPONENT",
                        message=f"Missing required strategy component: {component}",
                        severity=SeverityLevel.ERROR,
                        field=f"strategy.{component}",
                    )
                )

        # Check strategy consistency
        if strategy.get("campaign_strategy", {}).get("goals"):
            goals = strategy["campaign_strategy"]["goals"]
            if isinstance(goals, str) and len(goals) < 10:
                warnings.append(
                    ValidationWarning(
                        code="TOO_SHORT_GOALS",
                        message="Campaign goals appear too brief",
                        field="campaign_strategy.goals",
                    )
                )

        # Platform compatibility check
        platforms = strategy.get("platform_strategy", {}).get("platforms", [])
        if platforms:
            for platform in platforms:
                platform_info = (
                    strategy.get("platform_strategy", {}).get("adaptations", {}).get(platform)
                )
                if not platform_info:
                    warnings.append(
                        ValidationWarning(
                            code="MISSING_PLATFORM_ADAPTATION",
                            message=f"No specific adaptation found for platform: {platform}",
                            field="platform_strategy.adaptations",
                        )
                    )

        # Compliance scores
        present_components = sum(1 for component in required_components if strategy.get(component))
        compliance_scores["required_components"] = (
            present_components / len(required_components) if required_components else 0
        )

        is_valid = len(errors) == 0

        return {
            "id": f"validation_strategy_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "strategy",
            "artifact_id": strategy.get("id", "unknown"),
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Ensure all strategy components are populated",
                "Add platform-specific adaptations for better targeting",
                "Define measurable campaign goals",
            ],
            "validated_by": "LLMService",
        }
