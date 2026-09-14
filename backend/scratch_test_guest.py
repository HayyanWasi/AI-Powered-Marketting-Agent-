import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

from src.cache.cache import SessionCache
from src.services.guest_profile_service import GuestProfileService
from src.services.guest_research import ExaGuestResearchProvider
from src.services.llm_service import LLMService


async def test():
    provider = ExaGuestResearchProvider(api_key=os.getenv("EXA_API_KEY"))
    llm = LLMService()
    cache = SessionCache()
    service = GuestProfileService(research_provider=provider, llm_service=llm, cache=cache)

    print("Searching for guest...")
    # Using force_refresh=True to bypass any caching
    profile = await service.get_fresh_profile(
        session_id="test_session",
        guest_name="Zia Ullah Khan agentic AI architect",
        company_name=None,
        force_refresh=True,
    )

    if profile:
        print("Profile found:")
        print("Name:", profile.full_name)
        print("Bio:", profile.professional_biography)
        print("Expertise:", profile.areas_of_expertise)
        print("Confidence Level:", profile.confidence_level)
    else:
        print("No profile generated.")


if __name__ == "__main__":
    asyncio.run(test())
