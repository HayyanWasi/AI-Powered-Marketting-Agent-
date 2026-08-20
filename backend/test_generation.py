import asyncio
import logging

from src.modules.ai_generation.services.ai_generation_service import AIGenerationService

logging.basicConfig(level=logging.INFO)


async def test_generation():
    service = AIGenerationService()

    # Mock generation context
    generation_context = {
        "campaign_context": {"goals": ["brand awareness"], "budget": 1000},
        "company_profile": {
            "company_name": "TestCorp",
        },
        "audience": {"segments": ["professionals"]},
        "platforms": ["instagram", "linkedin"],
        "brand_guidelines": {
            "voice_tone": "professional and approachable",
            "guidelines": "Use blue colors",
        },
        "reference_materials": [],
    }

    try:
        result = await service.generate(generation_context)
        print("Generation successful!")
        print("Keys in result:", result.keys())
        print("Validation results:", result.get("validation"))
    except Exception as e:
        print(f"Generation failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_generation())
