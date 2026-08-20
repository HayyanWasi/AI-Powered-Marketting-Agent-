import os
import sys

from dotenv import load_dotenv

# Add backend directory to path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

import logging

from src.modules.ai_generation.services.ai_generation_service import AIGenerationService

logging.basicConfig(level=logging.INFO)

service = AIGenerationService()

context = {
    "campaign_context": {
        "name": "Summer Sale",
        "goals": ["brand awareness", "sales"],
        "start_date": "2026-06-01",
    },
    "company_profile": {
        "name": "Tech Corp",
    },
    "audience": {
        "segments": ["Millennials", "Gen Z"],
        "demographics": {"age": "18-35"},
        "interests": ["tech", "gadgets"],
    },
    "platforms": ["instagram", "twitter"],
    "brand_guidelines": {
        "voice_tone": "fun and energetic",
    },
    "user_intent": "Launch our new smartwatch with a blast",
}

print("Running campaign generation pipeline...")
import asyncio


async def main():
    try:
        # The method might be `generate` not `generate_campaign` based on the method list
        result = await service.generate(context)
        print("Generation successful!")
        print(f"Valid: {result['validation']['is_valid']}")
        if not result["validation"]["is_valid"]:
            print(f"Errors: {result['validation'].get('errors')}")
            print(f"Warnings: {result['validation'].get('warnings')}")
        print(f"Image URL: {result['images'][0].get('image_url')}")
    except Exception as e:
        print(f"Generation failed: {e}")


asyncio.run(main())
