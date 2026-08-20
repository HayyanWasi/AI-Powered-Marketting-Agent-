import asyncio

from src.modules.research.services.llm_router import LLMRouterService


async def main():
    router = LLMRouterService()
    print('Testing Qwen with No-Think instruction...')
    try:
        res = await router.generate_json(
            'You are a helpful assistant. DO NOT use <think> tags. Do not output any reasoning.',
            'Reply with {"status": "success"}'
        )
        print('Result:', res)
    except Exception as e:
        print('Failed:', e)

if __name__ == "__main__":
    asyncio.run(main())
