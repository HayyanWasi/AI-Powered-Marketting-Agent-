"""AI Generation Engine Service - Public Interface."""

from datetime import datetime
from typing import Any

from .context_builder_service import ContextBuilderService
from .image_generator_service import ImageGeneratorService
from .image_prompt_service import ImagePromptService
from .strategy_planner_service import StrategyPlannerService
from .validation_service import ValidationService


class AIGenerationService:
    """Public interface for AI Generation Engine - stateless content generation."""

    def __init__(self):
        self.context_builder = ContextBuilderService()
        self.strategy_planner = StrategyPlannerService()
        self.copy_generator = None
        self.image_prompt_generator = ImagePromptService()
        self.image_generator = ImageGeneratorService()
        self.validator = ValidationService()

    from langsmith import traceable

    @traceable(name="generate_campaign")
    async def generate(
        self,
        generation_context: dict[str, Any],
    ) -> dict[str, Any]:
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
        _ = await self._execute_generation_pipeline(generation_context)
        return _

    @traceable(name="regenerate_text")
    async def regenerate_text(
        self,
        generation_context: dict[str, Any],
        user_instructions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Regenerate text content while preserving strategy and images.
        """
        return await self._execute_text_regeneration_pipeline(generation_context, user_instructions)

    @traceable(name="regenerate_image")
    async def regenerate_image(
        self,
        generation_context: dict[str, Any],
        user_instructions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Regenerate images while preserving strategy and copy.
        """
        return await self._execute_image_regeneration_pipeline(
            generation_context, user_instructions
        )

    async def validate_all_artifacts(
        self,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate all campaign artifacts against business rules.

        Args:
            artifacts: Dictionary containing all campaign artifacts

        Returns:
            Dict containing comprehensive validation results and recommendations
        """
        return self.validator.validate_all_artifacts(artifacts)

    async def _execute_generation_pipeline(
        self, generation_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute complete generation pipeline: Context -> Strategy -> Copy -> Image Prompt -> Image -> Validate."""
        try:
            strategy = await self.strategy_planner.generate_strategy(generation_context)
            copy = await self._generate_copy(strategy, generation_context)
            platforms = generation_context.get("platforms", ["web"])
            primary_platform = platforms[0] if platforms else "web"
            image_prompt = self.image_prompt_generator.generate_image_prompt(
                strategy, copy, primary_platform
            )
            image = await self.image_generator.generate_image(image_prompt)
            validation = self.validator.validate_all_artifacts(
                {
                    "strategy": strategy,
                    "copy": [copy],
                    "image_prompts": [image_prompt],
                    "images": [image],
                }
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

    async def _execute_text_regeneration_pipeline(
        self,
        generation_context: dict[str, Any],
        user_instructions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute text regeneration pipeline preserving strategy and images."""
        try:
            strategy = generation_context.get("strategy")
            if not strategy:
                strategy = await self.strategy_planner.generate_strategy(generation_context)

            existing_image = generation_context.get("image")
            new_copy = await self._regenerate_copy(strategy, generation_context, user_instructions)
            validation = self.validator.validate_all_artifacts(
                {
                    "strategy": strategy,
                    "copy": [new_copy],
                    "images": [existing_image] if existing_image else [],
                }
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

    async def _execute_image_regeneration_pipeline(
        self,
        generation_context: dict[str, Any],
        user_instructions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute image regeneration pipeline preserving strategy and copy."""
        try:
            strategy = generation_context["strategy"]
            existing_copy = generation_context["copy"]
            platforms = generation_context.get("platforms", ["web"])
            primary_platform = platforms[0] if platforms else "web"
            new_image_prompt = self.image_prompt_generator.regenerate_image_prompt(
                strategy, existing_copy, primary_platform, user_instructions
            )
            new_image = await self.image_generator.regenerate_image(
                generation_context["image"], new_image_prompt, user_instructions
            )
            validation = self.validator.validate_all_artifacts(
                {
                    "strategy": strategy,
                    "copy": [existing_copy],
                    "image_prompts": [new_image_prompt],
                    "images": [new_image],
                }
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

    async def _generate_copy(
        self, strategy: dict[str, Any], generation_context: dict[str, Any]
    ) -> Any:
        """Generate copy content from strategy and context using LLM."""
        goals = strategy.get("campaign_strategy", {}).get("goals", [])
        primary_goal = goals[0] if goals else "Campaign"
        platforms = generation_context.get("platforms", ["web"])
        primary_platform = platforms[0] if platforms else "web"

        import json

        from src.modules.ai_generation.services.llm_service import LLMService

        system_prompt = "You are an expert copywriter. Based on the strategy and context provided, generate high-converting marketing copy. Your output MUST be a JSON object containing EXACTLY these keys: 'headlines' (list of strings), 'captions' (list of strings), 'ctas' (list of strings), 'hashtags' (list of strings), 'platform_variations' (dict mapping each platform to {'headline', 'body', 'cta', 'hashtags'})."

        user_prompt = json.dumps(
            {"strategy": strategy, "platforms": platforms, "primary_goal": primary_goal}
        )

        llm = LLMService()
        trace_id = generation_context.get("trace_id")
        workflow_id = generation_context.get("workflow_id")

        generated_data = await llm.generate_json(
            system_prompt,
            user_prompt,
            trace_id=trace_id,
            workflow_id=workflow_id,
            prompt_name="generate_copy",
        )

        if not generated_data:
            # Fallback to deterministic mock copy
            generated_data = {
                "headlines": [
                    f"Introducing {primary_goal}",
                    "Your target audience solution",
                    "Transform user experience",
                ],
                "captions": ["Professional marketing content aligned with brand voice"],
                "ctas": ["Learn More", "Get Started", "Contact Us"],
                "hashtags": ["#Marketing", "#Campaign", "#Brand"],
                "platform_variations": {
                    platform: {
                        "headline": f"Headline for {platform}",
                        "body": "Platform-specific body copy",
                        "cta": "Platform CTA",
                        "hashtags": "Platform hashtags",
                    }
                    for platform in platforms
                },
            }

        return {
            "id": f"copy_{hash(str(strategy)) % 10000}",
            "generated_at": datetime.now().isoformat(),
            "platform": primary_platform,
            **generated_data,
        }

    async def _regenerate_copy(
        self,
        strategy: dict[str, Any],
        generation_context: dict[str, Any],
        user_instructions: dict[str, Any] | None = None,
    ) -> Any:
        """Regenerate copy content preserving strategy."""
        if user_instructions and user_instructions.get("changes"):
            return {
                "id": f"copy_{hash(str(strategy) + str(user_instructions)) % 10000}",
                "generated_at": datetime.now().isoformat(),
                "platform": generation_context.get("copy", {}).get("platform", "web"),
                "headlines": [
                    f"Updated: {user_instructions['changes'].get('headline', 'New headline')}"
                ],
                "captions": ["Updated body copy based on user instructions"],
                "ctas": ["Updated CTA"],
                "hashtags": ["#Updated", "#Campaign"],
                "platform_variations": generation_context.get("copy", {}).get(
                    "platform_variations", {}
                ),
            }
        else:
            return generation_context.get("copy") or (
                await self._generate_copy(strategy, generation_context)
            )
