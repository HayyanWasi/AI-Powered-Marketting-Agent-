"""Prompt service for AI Generation Engine."""

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


class ImagePromptService:
    """Service for generating image prompts from strategy and copy artifacts."""

    from langsmith import traceable

    @traceable(name="generate_image_prompt")
    def generate_image_prompt(
        self,
        strategy_artifact: dict[str, Any],
        copy_artifact: dict[str, Any],
        platform: str,
    ) -> dict[str, Any]:
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
        # Validate input artifacts
        validation = self.validate_inputs(strategy_artifact, copy_artifact, platform)
        if not validation["is_valid"]:
            raise ValueError(f"Invalid inputs for image prompt generation: {validation['errors']}")

        # Extract relevant information from artifacts
        strategy_id = strategy_artifact.get("id", "unknown_strategy")
        copy_id = copy_artifact.get("id", "unknown_copy")

        # Generate deterministic image prompt based on input
        audience_segments = strategy_artifact.get("audience_strategy", {}).get(
            "target_segments", []
        )
        brand_voice = strategy_artifact.get("messaging_strategy", {}).get("tone", "professional")
        campaign_goals = strategy_artifact.get("campaign_strategy", {}).get("goals", [])

        # Create style guidelines from strategy
        style_guidelines = {
            "artistic_style": self._determine_artistic_style(audience_segments, campaign_goals),
            "color_scheme": self._derive_color_scheme(strategy_artifact, platform),
            "visual_mood": self._derive_visual_mood(brand_voice, campaign_goals),
            "typography": self._derive_typography(brand_voice),
            "composition": self._derive_composition(platform),
            "lighting": self._derive_lighting(campaign_goals),
            "filters": [],
        }

        # Create brand elements from brand guidelines
        brand_guidelines = strategy_artifact.get("brand_guidelines", {})
        brand_elements = self._create_brand_elements(brand_guidelines)

        # Create visual elements based on strategy and copy
        visual_elements = self._create_visual_elements(strategy_artifact, copy_artifact)

        # Create composition guidelines
        composition_guidelines = self._create_composition_guidelines(platform, audience_segments)

        # Generate prompt text
        prompt_text = self._generate_prompt_text(
            strategy_artifact, copy_artifact, platform, style_guidelines
        )

        image_prompt = {
            "id": f"image_prompt_{hash(str(strategy_artifact) + str(copy_artifact)) % 10000}",
            "generated_at": datetime.now().isoformat(),
            "strategy_id": strategy_id,
            "copy_id": copy_id,
            "platform": platform,
            "prompt_text": prompt_text,
            "style_guidelines": style_guidelines,
            "brand_elements": brand_elements,
            "visual_elements": visual_elements,
            "composition_guidelines": composition_guidelines,
            "validation_results": None,
        }

        return image_prompt

    @traceable(name="regenerate_image_prompt")
    def regenerate_image_prompt(
        self,
        strategy_artifact: dict[str, Any],
        copy_artifact: dict[str, Any],
        platform: str,
        user_instructions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Regenerate image prompt with user instructions."""
        # For simplicity, we just generate a new prompt and append user instructions if any
        prompt = self.generate_image_prompt(strategy_artifact, copy_artifact, platform)
        if user_instructions and user_instructions.get("changes"):
            changes = user_instructions["changes"].get("image_prompt", "")
            if changes:
                prompt["prompt_text"] += f". Additional instructions: {changes}"
                prompt["id"] = (
                    f"image_prompt_{hash(str(strategy_artifact) + str(copy_artifact) + str(user_instructions)) % 10000}"
                )
        return prompt

    def validate_image_prompt(
        self,
        prompt: dict[str, Any],
        strategy: dict[str, Any],
        copy: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate image prompt against strategy and copy.

        Args:
            prompt: Image prompt to validate
            strategy: Source strategy artifact
            copy: Source copy artifact

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
            if prompt.get(field) is None:
                errors.append(
                    ValidationError(
                        code="MISSING_PROMPT_FIELD",
                        message=f"Missing required image prompt field: {field}",
                        severity=SeverityLevel.ERROR,
                        field=f"image_prompt.{field}",
                    )
                )

        # Validate prompt consistency with strategy
        if prompt.get("strategy_id") != strategy.get("id"):
            warnings.append(
                ValidationWarning(
                    code="STRATEGY_ID_MISMATCH",
                    message="Image prompt strategy ID does not match source strategy",
                    field="image_prompt.strategy_id",
                )
            )

        if prompt.get("copy_id") != copy.get("id"):
            warnings.append(
                ValidationWarning(
                    code="COPY_ID_MISMATCH",
                    message="Image prompt copy ID does not match source copy",
                    field="image_prompt.copy_id",
                )
            )

        # Validate platform consistency
        strategy_platforms = strategy.get("platform_strategy", {}).get("platforms", [])
        prompt_platform = prompt.get("platform")
        if strategy_platforms and prompt_platform and prompt_platform not in strategy_platforms:
            warnings.append(
                ValidationWarning(
                    code="PLATFORM_NOT_IN_STRATEGY",
                    message=f"Prompt platform '{prompt_platform}' not in strategy platforms",
                    field="image_prompt.platform",
                )
            )

        # Validate brand alignment
        brand_elements = prompt.get("brand_elements", [])
        if not brand_elements:
            warnings.append(
                ValidationWarning(
                    code="NO_BRAND_ELEMENTS",
                    message="Image prompt contains no brand elements",
                    field="image_prompt.brand_elements",
                )
            )

        # Compliance scores
        present_fields = sum(1 for field in required_fields if prompt.get(field))
        compliance_scores["required_fields"] = (
            present_fields / len(required_fields) if required_fields else 0
        )

        is_valid = len(errors) == 0

        return {
            "id": f"validation_prompt_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "image_prompt",
            "artifact_id": prompt.get("id", "unknown"),
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Ensure all required fields are populated",
                "Match strategy and copy IDs consistently",
                "Use brand elements for brand alignment",
            ],
            "validated_by": "ImagePromptService",
        }

    def validate_inputs(
        self,
        strategy_artifact: dict[str, Any],
        copy_artifact: dict[str, Any],
        platform: str,
    ) -> dict[str, Any]:
        """
        Validate input artifacts for image prompt generation.

        Args:
            strategy_artifact: Strategy artifact to validate
            copy_artifact: Copy artifact to validate
            platform: Platform to validate

        Returns:
            ValidationArtifact: Validation results
        """
        errors = []
        warnings = []
        compliance_scores = {}

        # Validate strategy artifact
        if not strategy_artifact.get("id"):
            errors.append(
                ValidationError(
                    code="MISSING_STRATEGY_ID",
                    message="Strategy artifact missing ID",
                    severity=SeverityLevel.ERROR,
                    field="strategy_artifact.id",
                )
            )

        if not strategy_artifact.get("audience_strategy"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_AUDIENCE_STRATEGY",
                    message="Strategy missing audience strategy",
                    field="strategy_artifact.audience_strategy",
                )
            )

        if not strategy_artifact.get("messaging_strategy"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_MESSAGING_STRATEGY",
                    message="Strategy missing messaging strategy",
                    field="strategy_artifact.messaging_strategy",
                )
            )

        # Validate copy artifact
        if not copy_artifact.get("id"):
            errors.append(
                ValidationError(
                    code="MISSING_COPY_ID",
                    message="Copy artifact missing ID",
                    severity=SeverityLevel.ERROR,
                    field="copy_artifact.id",
                )
            )

        if not copy_artifact.get("platform"):
            errors.append(
                ValidationError(
                    code="MISSING_COPY_PLATFORM",
                    message="Copy artifact missing platform",
                    severity=SeverityLevel.ERROR,
                    field="copy_artifact.platform",
                )
            )

        if copy_artifact.get("platform") != platform:
            warnings.append(
                ValidationWarning(
                    code="PLATFORM_MISMATCH",
                    message="Copy platform does not match requested platform",
                    field="copy_artifact.platform",
                )
            )

        # Validate platform availability
        strategy_platforms = strategy_artifact.get("platform_strategy", {}).get("platforms", [])
        if strategy_platforms and platform not in strategy_platforms:
            warnings.append(
                ValidationWarning(
                    code="PLATFORM_NOT_SUPPORTED",
                    message=f"Platform '{platform}' not in strategy platforms {strategy_platforms}",
                    field="platform",
                )
            )

        # Compliance scores
        required_checks = 5
        passed_checks = 0

        if strategy_artifact.get("id"):
            passed_checks += 1
        if copy_artifact.get("id"):
            passed_checks += 1
        if copy_artifact.get("platform"):
            passed_checks += 1
        if strategy_platforms:
            passed_checks += 1
        if platform:
            passed_checks += 1

        compliance_scores["input_validity"] = (
            passed_checks / required_checks if required_checks > 0 else 0
        )

        is_valid = len(errors) == 0

        return {
            "id": f"validation_inputs_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "inputs",
            "artifact_id": "generation_validation",
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Provide valid strategy and copy artifacts",
                "Ensure strategy and copy are compatible",
                "Use supported platforms for generation",
            ],
            "validated_by": "ImagePromptService",
        }

    def _determine_artistic_style(
        self,
        audience_segments: list[str],
        campaign_goals: list[str],
    ) -> str:
        """Determine artistic style based on audience and goals."""
        if "professional" in str(audience_segments).lower():
            return "corporate_professional"
        elif "tech" in str(audience_segments).lower():
            return "modern_technology"
        elif "lifestyle" in str(audience_segments).lower():
            return "lifestyle_branding"
        else:
            return "professional_marketing"

    def _derive_color_scheme(
        self,
        strategy_artifact: dict[str, Any],
        platform: str,
    ) -> list[str]:
        """Derive color scheme from strategy and platform."""
        brand_guidelines = strategy_artifact.get("brand_guidelines", {})
        color_palette = brand_guidelines.get("color_palette", [])

        if platform == "linkedin":
            return color_palette + ["#0077B5"]
        elif platform == "instagram":
            return color_palette + ["#E1306C"]
        elif platform == "facebook":
            return color_palette + ["#1877F2"]
        else:
            return color_palette

    def _derive_visual_mood(
        self,
        brand_voice: str,
        campaign_goals: list[str],
    ) -> str:
        """Derive visual mood from brand voice and goals."""
        if "professional" in brand_voice.lower():
            return "trustworthy_institutional"
        elif "casual" in brand_voice.lower():
            return "approachable_friendly"
        elif "innovative" in str(campaign_goals).lower():
            return "cutting_edge_dynamic"
        else:
            return "clean_professional"

    def _derive_typography(self, brand_voice: str) -> str:
        """Derive typography from brand voice."""
        if "modern" in brand_voice.lower():
            return "sans_serif"
        elif "classic" in brand_voice.lower():
            return "serif"
        elif "minimalist" in brand_voice.lower():
            return "clean_sans"
        else:
            return "professional_sans"

    def _derive_composition(self, platform: str) -> str:
        """Derive composition based on platform."""
        if platform == "instagram":
            return "rule_of_thirds"
        elif platform == "linkedin":
            return "centered_header_footer"
        elif platform == "facebook":
            return "asymmetric_balanced"
        else:
            return "rule_of_thirds"

    def _derive_lighting(self, campaign_goals: list[str]) -> str:
        """Derive lighting style from campaign goals."""
        if any("awareness" in str(goal).lower() for goal in campaign_goals):
            return "bright_purposeful"
        elif any("professional" in str(goal).lower() for goal in campaign_goals):
            return "clean_sharp"
        elif any("premium" in str(goal).lower() for goal in campaign_goals):
            return "luxurious_rich"
        else:
            return "professional_standard"

    def _create_brand_elements(
        self,
        brand_guidelines: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Create brand elements from guidelines."""
        brand_elements = []

        # Logo
        logo_specs = brand_guidelines.get("logo_specs", {})
        if logo_specs:
            brand_elements.append(
                {
                    "element_type": "logo",
                    "location": "top-left",
                    "opacity": 1.0,
                    "size_spec": {
                        "width": logo_specs.get("width", 200),
                        "height": logo_specs.get("height", 80),
                    },
                }
            )

        # Colors
        color_palette = brand_guidelines.get("color_palette", [])
        for i, color in enumerate(color_palette[:3]):  # Use first 3 colors
            brand_elements.append(
                {
                    "element_type": "color_palette",
                    "location": "background",
                    "opacity": 0.3 - (i * 0.1),
                    "size_spec": {"type": "background_fill"},
                }
            )

        # Tagline
        brand_values = brand_guidelines.get("brand_values", [])
        if brand_values:
            brand_elements.append(
                {
                    "element_type": "tagline",
                    "location": "bottom_center",
                    "opacity": 0.8,
                    "size_spec": {"width": 400, "height": 50},
                }
            )

        # Fallback: Support string-based schema if no detailed structure exists
        tone = (
            brand_guidelines.get("voice_tone")
            or brand_guidelines.get("brand_tone")
            or brand_guidelines.get("tone")
        )
        guidelines = (
            brand_guidelines.get("brand_guidelines") or brand_guidelines.get("guidelines") or ""
        )
        if not brand_elements and (tone or guidelines):
            brand_elements.append(
                {
                    "element_type": "general_guidelines",
                    "description": f"Follow brand tone: {tone or 'professional'}. {str(guidelines)[:100]}",
                    "location": "overall",
                    "opacity": 1.0,
                    "size_spec": {"type": "thematic_influence"},
                }
            )

        return brand_elements

    def _create_visual_elements(
        self,
        strategy_artifact: dict[str, Any],
        copy_artifact: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Create visual elements based on strategy and copy."""
        visual_elements = []

        # Product/service concepts
        campaign_goals = strategy_artifact.get("campaign_strategy", {}).get("goals", [])
        for goal in campaign_goals[:2]:  # Limit to 2 concepts
            visual_elements.append(
                {
                    "concept": goal,
                    "description": self._generate_visual_description(goal),
                    "priority": 1,
                    "inclusion_requirement": True,
                }
            )

        # Platform-specific elements
        copy_headlines = copy_artifact.get("headlines", [])
        for i, headline in enumerate(copy_headlines[:2]):
            visual_elements.append(
                {
                    "concept": f"headline_visual_{i+1}",
                    "description": f"Visual representation of concept: {headline}",
                    "priority": 2,
                    "inclusion_requirement": True,
                }
            )

        return visual_elements

    def _generate_visual_description(self, goal: str) -> str:
        """Generate visual description for a concept."""
        return f"A professional visualization representing {goal} with clean composition and modern aesthetics"

    def _create_composition_guidelines(
        self,
        platform: str,
        audience_segments: list[str],
    ) -> dict[str, Any]:
        """Create composition guidelines for platform and audience."""
        return {
            "layout_type": "rule_of_thirds" if platform != "linkedin" else "centered_header_footer",
            "focal_points": ["top-left", "center", "bottom-right"],
            "depth_of_field": "deep" if platform == "instagram" else "standard",
            "perspective": "overhead" if platform == "instagram" else "eye_level",
            "negative_space": "moderate" if platform == "linkedin" else "balanced",
        }

    def _generate_prompt_text(
        self,
        strategy_artifact: dict[str, Any],
        copy_artifact: dict[str, Any],
        platform: str,
        style_guidelines: dict[str, Any],
    ) -> str:
        """Generate complete image prompt text."""
        campaign_context = strategy_artifact.get("campaign_context", {})
        campaign_name = campaign_context.get("name", "Campaign")

        audience_segments = strategy_artifact.get("audience_strategy", {}).get(
            "target_segments", []
        )
        copy_headlines = copy_artifact.get("headlines", [])
        brand_guidelines = strategy_artifact.get("brand_guidelines", {})
        brand_voice = brand_guidelines.get("voice_tone", "professional")

        prompt_parts = [
            f"Professional marketing image for {campaign_name}",
            f"Target audience: {', '.join(audience_segments)}",
            f"Brand voice: {brand_voice}",
            f"Platform: {platform}",
        ]

        if copy_headlines:
            prompt_parts.append(f"Key message concept: {copy_headlines[0]}")

        style_desc = f"{style_guidelines['artistic_style'].replace('_', ' ')} style"
        prompt_parts.append(f"Visual style: {style_desc}")

        color_desc = f"colors: {', '.join(style_guidelines['color_scheme'][:3])}"
        prompt_parts.append(f"Color palette: {color_desc}")

        mood_desc = f"mood: {style_guidelines['visual_mood'].replace('_', ' ')}"
        prompt_parts.append(f"Visual mood: {mood_desc}")

        composition_desc = f"composition: {style_guidelines['composition'].replace('_', ' ')}"
        prompt_parts.append(f"Composition: {composition_desc}")

        lighting_desc = f"lighting: {style_guidelines['lighting'].replace('_', ' ')}"
        prompt_parts.append(f"Lighting: {lighting_desc}")

        brand_elements = [
            "brand logo",
            "company colors",
            f"brand values: {', '.join(brand_guidelines.get('brand_values', [])[:2])}",
        ]
        prompt_parts.append(f"Brand elements: {', '.join(brand_elements)}")

        if style_guidelines["filters"]:
            prompt_parts.append(f"Image enhancement: {style_guidelines['filters'][0]}")

        prompt_parts.append("high quality professional photography")
        prompt_parts.append("commercial marketing use")

        return ", ".join(prompt_parts)
