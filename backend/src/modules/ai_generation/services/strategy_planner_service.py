"""Strategy planner service for AI Generation Engine."""

from datetime import datetime
from typing import Any

from ..constants import SeverityLevel


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


class StrategyPlannerService:
    """Service for planning campaign strategy from generation context."""

    from langsmith import traceable

    @traceable(name="generate_strategy")
    async def generate_strategy(
        self,
        generation_context: dict[str, Any],
    ) -> dict[str, Any]:
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
        # Validate input context
        validation = self.validate_strategy_input(generation_context)
        if not validation["is_valid"]:
            raise ValueError(
                f"Invalid generation context for strategy planning: {validation['errors']}"
            )

        # Extract context components
        campaign_context = generation_context.get("campaign_context", {})
        company_profile = generation_context.get("company_profile", {})
        audience = generation_context.get("audience", {})
        platforms = generation_context.get("platforms", [])
        brand_guidelines = generation_context.get("brand_guidelines", {})
        user_intent = generation_context.get("user_intent")

        strategy_id = f"strategy_{hash(str(generation_context)) % 10000}"

        import json

        from src.modules.ai_generation.services.llm_service import LLMService

        system_prompt = """You are an expert marketing strategist. Given the context about a campaign, generate a detailed campaign strategy. 
Your output MUST be a JSON object containing EXACTLY these top-level keys:
- "audience_strategy" (dict with "target_segments" list, "demographics" dict, "interests" list, "positioning", "messaging_guidelines" dict with "tone" and "key_points")
- "messaging_strategy" (dict with "headline_approaches" list, "supporting_points" list, "emotional_appeal", "brand_alignment")
- "platform_strategy" (dict with "platforms" list, "adaptations" dict mapping platform to {"format", "length_limit", "media_requirements", "hashtag_guidelines" list})
- "seo_strategy" (dict with "primary_keywords", "secondary_keywords", "meta_descriptions", "content_structure" list)
- "campaign_strategy" (dict with "goals" list, "target_metrics" dict, "timeline" dict, "budget_distribution" dict, "approval_required" list)
"""
        user_prompt = json.dumps(
            {
                "campaign_context": campaign_context,
                "company_profile": company_profile,
                "audience": audience,
                "platforms": platforms,
                "brand_guidelines": brand_guidelines,
                "user_intent": user_intent,
            }
        )

        llm = LLMService()
        trace_id = generation_context.get("trace_id")
        workflow_id = generation_context.get("workflow_id")

        generated_data = await llm.generate_json(
            system_prompt,
            user_prompt,
            trace_id=trace_id,
            workflow_id=workflow_id,
            prompt_name="generate_strategy",
        )

        if not generated_data:
            # Fallback to deterministic strategy
            segments = audience.get("segments", [])
            primary_segment = segments[0] if segments else "target"
            generated_data = {
                "audience_strategy": {
                    "target_segments": audience.get("segments", []),
                    "demographics": audience.get("demographics", {}),
                    "interests": audience.get("interests", []),
                    "positioning": f"Positioning based on {company_profile.get('name', 'company')}'s values",
                    "messaging_guidelines": {
                        "tone": brand_guidelines.get("voice_tone", "professional"),
                        "key_points": campaign_context.get("goals", []),
                    },
                },
                "messaging_strategy": {
                    "headline_approaches": [
                        f"Introducing {campaign_context.get('name', 'new campaign')}",
                        f"Your {primary_segment} solution",
                        f"Transform {primary_segment} experience",
                    ],
                    "supporting_points": [
                        "Innovative approach to industry challenges",
                        "Proven results and measurable impact",
                        "Tailored to specific audience needs",
                    ],
                    "emotional_appeal": "confidence and opportunity",
                    "brand_alignment": brand_guidelines.get("voice_tone", "professional"),
                },
                "platform_strategy": {
                    "platforms": platforms,
                    "adaptations": {
                        platform: {
                            "format": (
                                "carousel" if platform in ["instagram", "facebook"] else "single"
                            ),
                            "length_limit": (
                                "280 characters" if platform == "twitter" else "unlimited"
                            ),
                            "media_requirements": (
                                "image" if platform in ["instagram", "facebook"] else "text"
                            ),
                            "hashtag_guidelines": [
                                f"#{campaign_context.get('name', 'campaign').replace(' ', '')}",
                                f"#{company_profile.get('name', 'company').replace(' ', '')}",
                            ],
                        }
                        for platform in platforms
                    },
                },
                "seo_strategy": {
                    "primary_keywords": [
                        campaign_context.get("name", "campaign"),
                        "marketing",
                        "strategy",
                    ],
                    "secondary_keywords": ["campaign management", "brand building"],
                    "meta_descriptions": f"Campaign focused on {primary_segment} goals",
                    "content_structure": ["headline", "body", "call_to_action"],
                },
                "campaign_strategy": {
                    "goals": campaign_context.get("goals", ["brand awareness", "lead generation"]),
                    "target_metrics": {
                        "engagement_rate": "5%",
                        "conversion_rate": "2%",
                        "reach": "100k users",
                    },
                    "timeline": {
                        "start_date": campaign_context.get("start_date", "2026-08-01"),
                        "duration": "30 days",
                        "peak_dates": ["2026-08-15", "2026-08-20"],
                    },
                    "budget_distribution": {
                        "paid_media": 0.6,
                        "organic": 0.2,
                        "creatives": 0.2,
                    },
                    "approval_required": ["creative concepts", "final copy"],
                },
            }

        strategy = {
            "id": strategy_id,
            "generated_at": datetime.now().isoformat(),
            **generated_data,
            "brand_guidelines": brand_guidelines,
            "validation_results": None,
        }

        return strategy

    def validate_strategy(
        self,
        strategy: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate generated strategy against business rules.

        Args:
            strategy: Strategy to validate

        Returns:
            ValidationArtifact: Validation results
        """
        errors = []
        warnings = []
        compliance_scores = {}

        # Check required fields
        required_fields = [
            "audience_strategy",
            "messaging_strategy",
            "platform_strategy",
            "seo_strategy",
            "campaign_strategy",
        ]

        for field in required_fields:
            if strategy.get(field) is None:
                errors.append(
                    ValidationError(
                        code="MISSING_STRATEGY_FIELD",
                        message=f"Missing required strategy field: {field}",
                        severity=SeverityLevel.ERROR,
                        field=f"strategy.{field}",
                    )
                )

        # Validate audience strategy
        audience_strategy = strategy.get("audience_strategy", {})
        if not audience_strategy.get("target_segments"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_AUDIENCE_SEGMENTS",
                    message="Audience segments are recommended for targeted content",
                    field="audience_strategy.target_segments",
                )
            )

        # Validate platform adaptations
        platform_adaptations = strategy.get("platform_strategy", {}).get("adaptations", {})
        if platform_adaptations:
            for platform, adaptation in platform_adaptations.items():
                if not adaptation.get("format"):
                    warnings.append(
                        ValidationWarning(
                            code="MISSING_PLATFORM_FORMAT",
                            message=f"Platform format not specified for {platform}",
                            field=f"platform_strategy.adaptations.{platform}.format",
                        )
                    )

                if not adaptation.get("length_limit"):
                    warnings.append(
                        ValidationWarning(
                            code="MISSING_LENGTH_LIMIT",
                            message=f"Content length limit not specified for {platform}",
                            field=f"platform_strategy.adaptations.{platform}.length_limit",
                        )
                    )

        # Validate campaign strategy
        campaign_strategy = strategy.get("campaign_strategy", {})
        if campaign_strategy.get("goals"):
            goals = campaign_strategy["goals"]
            if isinstance(goals, list) and len(goals) == 0:
                warnings.append(
                    ValidationWarning(
                        code="EMPTY_CAMPAIGN_GOALS",
                        message="Campaign goals are empty - this strategy may lack direction",
                        field="campaign_strategy.goals",
                    )
                )

        # Compliance scores
        present_fields = sum(1 for field in required_fields if strategy.get(field))
        compliance_scores["required_fields"] = (
            present_fields / len(required_fields) if required_fields else 0
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
                "Populate all required strategy fields",
                "Define specific audience segments for better targeting",
                "Add platform-specific adaptations for each target platform",
                "Set clear campaign goals with measurable metrics",
            ],
            "validated_by": "StrategyPlannerService",
        }

    def validate_strategy_input(
        self,
        generation_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate generation context for strategy generation.

        Args:
            generation_context: Generation context to validate

        Returns:
            ValidationArtifact: Validation results
        """
        errors = []
        warnings = []
        compliance_scores = {}

        # Required fields for strategy generation
        required_fields = [
            "campaign_context",
            "company_profile",
            "audience",
            "platforms",
            "brand_guidelines",
        ]

        for field in required_fields:
            if generation_context.get(field) is None:
                errors.append(
                    ValidationError(
                        code="MISSING_CONTEXT_FIELD",
                        message=f"Missing required context field for strategy: {field}",
                        severity=SeverityLevel.ERROR,
                        field=f"context.{field}",
                    )
                )

        # Validate campaign context completeness
        campaign_context = generation_context.get("campaign_context", {})
        if not campaign_context.get("name"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_CAMPAIGN_NAME",
                    message="Campaign name is recommended for strategy generation",
                    field="campaign_context.name",
                )
            )

        # Validate audience completeness
        audience = generation_context.get("audience", {})
        if not audience.get("segments"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_AUDIENCE_SEGMENTS",
                    message="Audience segments are required for strategy planning",
                    field="audience.segments",
                )
            )

        # Validate platform list
        platforms = generation_context.get("platforms", [])
        if not platforms:
            errors.append(
                ValidationError(
                    code="NO_PLATFORMS_SPECIFIED",
                    message="At least one platform must be specified for strategy generation",
                    severity=SeverityLevel.ERROR,
                    field="platforms",
                )
            )
        elif len(platforms) > 10:
            warnings.append(
                ValidationWarning(
                    code="TOO_MANY_PLATFORMS",
                    message="Many platforms specified - strategy may be too dispersed",
                    field="platforms",
                )
            )

        # Validate brand guidelines
        brand_guidelines = generation_context.get("brand_guidelines", {})
        if not brand_guidelines.get("voice_tone"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_BRAND_VOICE",
                    message="Brand voice tone is recommended for consistent strategy",
                    field="brand_guidelines.voice_tone",
                )
            )

        # Compliance scores
        present_fields = sum(1 for field in required_fields if generation_context.get(field))
        compliance_scores["required_fields"] = (
            present_fields / len(required_fields) if required_fields else 0
        )

        is_valid = len(errors) == 0

        return {
            "id": f"validation_context_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "generation_context",
            "artifact_id": "context_validation",
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Include all required context fields before strategy generation",
                "Add campaign name for better strategy context",
                "Define specific audience segments for targeting",
                "Specify at least one primary platform",
                "Establish brand voice guidelines for consistency",
            ],
            "validated_by": "StrategyPlannerService",
        }
