import asyncio
import logging

from src.modules.ai_generation.services.image_generator_service import ImageGeneratorService

logging.basicConfig(level=logging.WARNING)


async def test_cf():
    service = ImageGeneratorService()
    try:
        url = await service._generate_image_url(
            image_prompt_artifact={
                "prompt_text": "A futuristic city skyline at sunset, cyberpunk style, vibrant colors"
            },
            strategy_id="test_strategy_123",
            copy_id="test_copy_123",
            platform="instagram",
        )
        print("Generated URL:", url)
    except Exception as e:
        print("Failed:", e)


if __name__ == "__main__":
    asyncio.run(test_cf())
