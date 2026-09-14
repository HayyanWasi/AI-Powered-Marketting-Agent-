import json
import logging

from src.models.image_generation import BrandSnapshot, ImageGenerationState
from src.modules.research.services.llm_router import LLMRouterService

logger = logging.getLogger(__name__)


class ImageIterativeService:
    def __init__(self, llm: LLMRouterService | None = None):
        self.llm = llm or LLMRouterService()

    async def _generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Helper: call generate_json and extract a plain text result from the response dict."""
        result = await self.llm.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prefer_gemini=True,
        )
        # generate_json returns a dict. If it has a 'text', 'content', or 'response' key use that.
        # Otherwise, JSON-serialize the whole dict as a fallback.
        for key in ("text", "content", "response", "result", "output"):
            if key in result and isinstance(result[key], str):
                return result[key]
        return json.dumps(result)

    async def _generate_json_fields(self, system_prompt: str, user_prompt: str) -> dict:
        """Helper: call generate_json and return parsed dict."""
        return await self.llm.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prefer_gemini=True,
        )

    async def initialize_state(self, base_idea: str, brand: BrandSnapshot) -> ImageGenerationState:
        system_prompt = (
            "You are an expert AI image prompt engineer. Always respond with valid JSON only."
        )
        user_prompt = f"""Take this user's base idea and brand profile, and generate a highly optimized prompt for an AI image generator (like Pollinations/Flux).

BASE IDEA:
{base_idea}

BRAND SNAPSHOT:
Brand Name: {brand.brand_name}
Industry: {brand.industry}
Tone of Voice: {brand.tone_of_voice}
Personality Descriptors: {', '.join(brand.personality_descriptors) if brand.personality_descriptors else 'Not specified'}
Color Palette: {', '.join(brand.color_palette) if brand.color_palette else 'Not specified'}
Style Guidance: {brand.style_guidance}

INSTRUCTIONS:
1. Brand Visual Translation: Translate brand metadata (especially hex codes and tone words) into literal visual language. E.g., #FF0000 → "vibrant reds", "bold" → "high contrast, dramatic lighting". DO NOT output raw hex codes.
2. Brand Adjustments: Briefly explain how you are molding the base idea using the visual translation.
3. Final Image Prompt: A single, highly descriptive prompt to send to the image generator.

Respond ONLY with valid JSON matching this exact schema:
{{
    "brand_visual_translation": "...",
    "brand_adjustments": "...",
    "current_final_prompt": "..."
}}"""

        try:
            data = await self._generate_json_fields(system_prompt, user_prompt)
        except Exception as e:
            logger.error("LLM call failed in initialize_state: %s", e)
            # Graceful fallback: use the base idea directly as the prompt
            data = {
                "brand_visual_translation": f"Brand: {brand.brand_name}, tone: {brand.tone_of_voice}",
                "brand_adjustments": "Using base idea directly due to LLM error.",
                "current_final_prompt": base_idea,
            }

        return ImageGenerationState(
            base_idea=base_idea,
            brand_snapshot=brand,
            brand_visual_translation=data.get("brand_visual_translation", ""),
            brand_adjustments=data.get("brand_adjustments", ""),
            current_final_prompt=data.get("current_final_prompt", base_idea),
            iteration_count=1,
        )

    async def refine_state(
        self, state: ImageGenerationState, instruction: str
    ) -> ImageGenerationState:
        system_prompt = "You are an expert AI image prompt engineer. Output only the refined prompt text with no markdown, quotes, or explanation."
        user_prompt = f"""Refine the following image prompt based on the user's instruction. Maintain brand visual constraints.

CURRENT PROMPT:
{state.current_final_prompt}

BRAND VISUAL CONSTRAINTS (maintain these):
{state.brand_visual_translation}

USER INSTRUCTION:
{instruction}

Output ONLY the new refined prompt as plain text. No JSON, no markdown, no quotes."""

        try:
            result = await self._generate_json_fields(system_prompt, user_prompt)
            # Try to extract plain text from result dict
            new_prompt = None
            for key in (
                "text",
                "content",
                "response",
                "result",
                "output",
                "prompt",
                "refined_prompt",
            ):
                if key in result and isinstance(result[key], str):
                    new_prompt = result[key].strip()
                    break
            if not new_prompt:
                # generate_json may have wrapped the plain text under any key
                new_prompt = next(
                    (v for v in result.values() if isinstance(v, str) and len(v) > 20),
                    state.current_final_prompt,
                )
        except Exception as e:
            logger.error("LLM call failed in refine_state: %s", e)
            new_prompt = f"{state.current_final_prompt}, {instruction}"

        state.current_final_prompt = new_prompt
        state.refinements.append(instruction)
        state.iteration_count += 1
        return state

    async def generate_caption(self, base_idea: str, tone: str) -> str:
        """Generate a LinkedIn post caption for the finalized image."""
        system_prompt = "You are a professional social media copywriter specializing in LinkedIn. Write engaging, professional captions."
        user_prompt = f"""Write a LinkedIn post caption for an image. 

Image concept: {base_idea}
Tone: {tone if tone else 'professional'}

Write a compelling caption with 2-3 short paragraphs and 3-5 relevant hashtags at the end. No JSON, plain text only."""

        try:
            result = await self._generate_json_fields(system_prompt, user_prompt)
            for key in ("text", "content", "response", "caption", "result", "output"):
                if key in result and isinstance(result[key], str):
                    return result[key].strip()
            return next(
                (v for v in result.values() if isinstance(v, str) and len(v) > 20),
                f"Check out this image about {base_idea}! #Marketing #AI",
            )
        except Exception as e:
            logger.error("Caption generation failed: %s", e)
            return f"Excited to share this visual! #{base_idea.split()[0] if base_idea else 'Marketing'} #AI #Innovation"
