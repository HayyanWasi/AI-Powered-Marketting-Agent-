"""AI Generation Engine Service - Public Interface."""

from datetime import datetime
from typing import Any, Dict, Optional

from .constants import SeverityLevel
from .models.generation_context import GenerationContext
from .services.context_builder_service import ContextBuilderService
from .services.image_generator_service import ImageGeneratorService
from .services.image_prompt_service import ImagePromptService
from .services.strategy_planner_service import StrategyPlannerService
from .services.validation_service import ValidationService


class AIGenerationService:
    """Public interface for AI Generation Engine - stateless content generation."""

    def __init__(self):
        self.context_builder = ContextBuilderService()
        self.strategy_planner = StrategyPlannerService()
        self.copy_generator = None
        self.image_prompt_generator = ImagePromptService()
        self.image_generator = ImageGeneratorService()
        self.validator = ValidationService()

    async def generate(
        self,
        generation_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate complete marketing campaign artifacts.

        Args:
            generation_context: Complete campaign context with company profile,
                                audience data, platforms, brand guidelines, reference materials

        Returns:
            Dict containing all generated artifacts and validation results

        Raises:
            ValueError: If generation context is invalid
        """
        _ = self._execute_generation_pipeline(generation_context)
        return _

    async def regenerate_text(
        self,
        generation_context: Dict[str, Any],
        user_instructions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Regenerate text content while preserving strategy and images.

        Args:
            generation_context: Complete generation context with existing artifacts
            user_instructions: Optional instructions for content regeneration

        Returns:
            Dict containing updated copy artifacts and validation results
        """
        return self._execute_text_regeneration_pipeline(generation_context, user_instructions)

    async def regenerate_image(
        self,
        generation_context: Dict[str, Any],
        user_instructions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Regenerate images while preserving strategy and copy.

        Args:
            generation_context: Complete generation context with existing artifacts
            user_instructions: Optional instructions for image regeneration

        Returns:
            Dict containing updated image artifacts and validation results
        """
        return self._execute_image_regeneration_pipeline(generation_context, user_instructions)

    async def validate_all_artifacts(
        self,
        artifacts: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate all campaign artifacts against business rules.

        Args:
            artifacts: Dictionary containing all campaign artifacts

        Returns:
            Dict containing comprehensive validation results and recommendations
        """
        return self.validator.validate_artifacts(artifacts)

    def _execute_generation_pipeline(self, generation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete generation pipeline: Context → Strategy → Copy → Image Prompt → Image → Validate."""
        try:
            strategy = self.strategy_planner.generate_strategy(generation_context)
            copy = self._generate_copy(strategy, generation_context)
            image_prompt = self.image_prompt_generator.generate_prompt(
                strategy, copy, generation_context
            )
            image = self.image_generator.generate_image(image_prompt)
            validation = self.validator.validate_artifacts(
                {"strategy": strategy, "copy": copy, "image_prompt": image_prompt, "image": image}
            )

            return {
                "strategy": strategy,
                "copy": copy,
                "image_prompt": image_prompt,
                "image": image,
                "validation": validation,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "pipeline_version": "1.0",
                },
            }
        except Exception as e:
            raise ValueError(f"Generation pipeline execution failed: {str(e)}")

    def _execute_text_regeneration_pipeline(
        self,
        generation_context: Dict[str, Any],
        user_instructions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute text regeneration pipeline preserving strategy and images."""
        try:
            strategy = generation_context["strategy"]
            existing_image = generation_context["image"]
            new_copy = self._regenerate_copy(strategy, generation_context, user_instructions)
            validation = self.validator.validate_artifacts(
                {"strategy": strategy, "copy": new_copy, "image": existing_image}
            )

            return {
                "strategy": strategy,
                "copy": new_copy,
                "image": existing_image,
                "validation": validation,
                "metadata": {
                    "updated_at": datetime.now().isoformat(),
                    "regeneration_type": "text",
                },
            }
        except Exception as e:
            raise ValueError(f"Text regeneration pipeline execution failed: {str(e)}")

    def _execute_image_regeneration_pipeline(
        self,
        generation_context: Dict[str, Any],
        user_instructions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute image regeneration pipeline preserving strategy and copy."""
        try:
            strategy = generation_context["strategy"]
            existing_copy = generation_context["copy"]
            new_image_prompt = self.image_prompt_generator.regenerate_prompt(
                strategy, existing_copy, user_instructions
            )
            new_image = self.image_generator.regenerate_image(
                generation_context["image"], new_image_prompt, user_instructions
            )
            validation = self.validator.validate_artifacts(
                {"strategy": strategy, "copy": existing_copy, "image": new_image}
            )

            return {
                "strategy": strategy,
                "copy": existing_copy,
                "image_prompt": new_image_prompt,
                "image": new_image,
                "validation": validation,
                "metadata": {
                    "updated_at": datetime.now().isoformat(),
                    "regeneration_type": "image",
                },
            }
        except Exception as e:
            raise ValueError(f"Image regeneration pipeline execution failed: {str(e)}")

    def _generate_copy(self, strategy: Dict[str, Any], generation_context: Dict[str, Any]) -> Any:
        """Generate copy content from strategy and context (placeholder for llm_service)."""
        return {
            "id": f"copy_{hash(str(strategy)) % 10000}",
            "generated_at": datetime.now().isoformat(),
            "headlines": [
                f"Introducing {strategy.get('campaign_strategy', {}).get('goals', ['Campaign'])[0]}",
                f"Your target audience solution",
                f"Transform user experience",
            ],
            "body_copy": "Professional marketing content aligned with brand voice",
            "call_to_actions": ["Learn More", "Get Started", "Contact Us"],
            "hashtags": ["#Marketing", "#Campaign", "#Brand"],
            "platform_variations": {
                platform: {
                    "headline": f"Headline for {platform}",
                    "body": "Platform-specific body copy",
                    "cta": "Platform CTA",
                    "hashtags": "Platform hashtags",
                }
                for platform in generation_context.get("platforms", [])
            },
        }

    def _regenerate_copy(
        self,
        strategy: Dict[str, Any],
        generation_context: Dict[str, Any],
        user_instructions: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Regenerate copy content preserving strategy."""
        if user_instructions and user_instructions.get("changes"):
            return {
                "id": f"copy_{hash(str(strategy + str(user_instructions))) % 10000}",
                "generated_at": datetime.now().isoformat(),
                "headlines": [
                    f"Updated: {user_instructions['changes'].get('headline', 'New headline')}"
                ],
                "body_copy": "Updated body copy based on user instructions",
                "call_to_actions": ["Updated CTA"],
                "hashtags": ["#Updated", "#Campaign"],
                "platform_variations": generation_context.get("copy", {}).get(
                    "platform_variations", {}
                ),
            }
        else:
            return generation_context.get("copy", self._generate_copy(strategy, generation_context))
