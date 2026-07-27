"""Context Builder — creates the immutable GenerationContext before workflow execution.

Rule: GenerationContext MUST be created before the first workflow node executes.
All subsequent nodes MUST consume only this context.
"""

import logging
from src.agents.context import (
    GenerationContext,
    BrandData,
    GuestData,
    EventData,
)

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds the GenerationContext from input data.

    This is the ONLY place that reads from persistent storage.
    Once the context is built, no agent reads from database again.
    """

    def __init__(self):
        self._brand_service = None
        self._guest_service = None

    def build(
        self,
        company_profile_id: str | None = None,
        guest_urls: list[str] | None = None,
        event_name: str = "",
        event_date: str = "",
        venue: str = "",
        platforms: list[str] | None = None,
        registration_link: str = "",
    ) -> GenerationContext:
        """Build the GenerationContext from input parameters.

        This method reads from persistent storage (company profiles,
        guest data) and creates an immutable snapshot.

        After this method returns, no agent should read from database.
        """
        logger.info("Building GenerationContext for event: %s", event_name)

        # Load brand data (would read from Supabase in production)
        brand = self._load_brand_data(company_profile_id)

        # Load guest data (would read from cache/search in production)
        guests = self._load_guest_data(guest_urls or [])

        # Build event data
        event = EventData(
            event_name=event_name,
            event_date=event_date,
            venue=venue,
            platforms=tuple(platforms or []),
            registration_link=registration_link,
        )

        context = GenerationContext(
            brand=brand,
            guests=tuple(guests),
            event=event,
        )

        logger.info(
            "Context built: brand=%s, guests=%d, platforms=%s",
            brand.company_name,
            len(guests),
            event.platforms,
        )

        return context

    def _load_brand_data(self, company_profile_id: str | None) -> BrandData:
        """Load brand data from company profile.

        In production, this calls CompanyRepository.get_by_id().
        """
        if not company_profile_id:
            return BrandData(company_name="")

        # TODO: Call CompanyRepository in production
        return BrandData(
            company_name="Example Corp",
            brand_guidelines="Professional, modern, innovative",
            brand_tone="Professional yet approachable",
            reference_image_urls=(),
        )

    def _load_guest_data(self, guest_urls: list[str]) -> list[GuestData]:
        """Load guest data from search/cache.

        In production, this calls GuestSearchService for each URL.
        """
        # TODO: Call GuestSearchService in production
        return []
