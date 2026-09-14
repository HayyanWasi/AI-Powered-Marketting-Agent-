"""Context Builder — creates the immutable GenerationContext before workflow execution.

Rule: GenerationContext MUST be created before the first workflow node executes.
All subsequent nodes MUST consume only this context.
"""

import logging
from uuid import UUID

from src.agents.context import (
    BrandData,
    EventData,
    GenerationContext,
    GuestData,
)
from src.services.supabase import NotFoundError, SupabaseService, SupabaseServiceError

logger = logging.getLogger(__name__)

# Number of guest search snippets folded into the biography context.
_MAX_GUEST_SNIPPETS = 3


class ContextBuilder:
    """Builds the GenerationContext from input data.

    This is the ONLY place that reads from persistent storage.
    Once the context is built, no agent reads from database again.
    """

    def __init__(
        self,
        supabase_service: SupabaseService | None = None,
    ) -> None:
        """Initialize the builder with the services it reads from.

        Args:
            supabase_service: Source of company brand data. Constructed lazily
                on first use if not provided (keeps tests offline-friendly).
        """
        self._brand_service = supabase_service
        self._guest_profile_service = None

    async def build(
        self,
        company_profile_id: str | None = None,
        guest_names: list[str] | None = None,
        event_name: str = "",
        event_date: str = "",
        venue: str = "",
        platforms: list[str] | None = None,
        registration_link: str = "",
        user_goal: str = "",
        campaign_id: UUID | None = None,
    ) -> GenerationContext:
        """Build the GenerationContext from input parameters.

        This method reads from persistent storage (company profiles,
        guest data, campaign plan) and creates an immutable snapshot.

        After this method returns, no agent should read from database.

        Args:
            company_profile_id: Company profile to load brand data from.
            guest_names: Guest/speaker names to research and snapshot.
            event_name: Event display name.
            event_date: Event date string.
            venue: Event venue.
            platforms: Target social platforms.
            registration_link: Event registration URL.
            user_goal: Free-text goal typed by the marketer.
            campaign_id: When provided, the approved plan for this campaign
                is attached.

        Returns:
            An immutable GenerationContext snapshot.
        """
        import asyncio

        logger.info("Building GenerationContext for event: %s", event_name)

        brand_task = asyncio.create_task(self._load_brand_data_async(company_profile_id))
        guest_task = asyncio.create_task(
            self._load_guest_data(guest_names or [], company_profile_id)
        )
        plan_task = asyncio.create_task(self._load_approved_plan(campaign_id))

        brand, guests, plan = await asyncio.gather(brand_task, guest_task, plan_task)

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
            user_goal=user_goal,
            plan=plan,
        )

        logger.info(
            "Context built: brand=%s, guests=%d, references=%d, platforms=%s, plan=%s",
            brand.company_name,
            len(guests),
            len(brand.reference_image_urls),
            event.platforms,
            "approved" if (plan and plan.approved) else ("unapproved" if plan else "none"),
        )

        return context

    async def _load_brand_data_async(self, company_profile_id: str | None) -> BrandData:
        """Async wrapper for loading brand data to allow it to run in gather."""
        import asyncio

        return await asyncio.to_thread(self._load_brand_data, company_profile_id)

    def _load_brand_data(self, company_profile_id: str | None) -> BrandData:
        """Load brand data from the company profile.

        Missing or unreadable brand data MUST NOT block generation
        (spec 007 FR-03); an empty BrandData is returned in that case so
        downstream agents fall back to prompt-only generation.

        Args:
            company_profile_id: Company profile identifier, or None.

        Returns:
            A BrandData snapshot (possibly empty).
        """
        if not company_profile_id:
            logger.info("No company_profile_id provided; brand styling unavailable")
            return BrandData(company_name="")

        service = self._get_brand_service()
        if service is None:
            return BrandData(company_name="")

        try:
            row = service.get_profile(company_profile_id)
        except NotFoundError:
            logger.warning(
                "Company profile %s not found; continuing without brand data",
                company_profile_id,
            )
            return BrandData(company_name="")
        except SupabaseServiceError as e:
            logger.warning(
                "Failed to load company profile %s (%s); continuing without brand data",
                company_profile_id,
                e,
            )
            return BrandData(company_name="")

        references = row.get("reference_image_urls") or ()
        return BrandData(
            company_name=row.get("company_name", ""),
            brand_guidelines=row.get("brand_guidelines", ""),
            brand_tone=row.get("brand_tone", ""),
            reference_image_urls=tuple(references),
            style_guide=row.get("brand_guidelines", ""),
        )

    async def _load_guest_data(
        self, guest_names: list[str], company_profile_id: str | None = None
    ) -> list[GuestData]:
        """Research and snapshot guest/speaker data concurrently.

        Args:
            guest_names: Names of guests/speakers to research.
            company_profile_id: Profile ID, to fetch company name if needed (optional).

        Returns:
            A list of GuestData snapshots.
        """
        if not guest_names:
            return []

        service = self._get_guest_service()
        if service is None:
            return []

        company_name = ""
        if company_profile_id:
            try:
                brand = self._load_brand_data(company_profile_id)
                company_name = brand.company_name
            except Exception:
                pass

        import asyncio

        # Generate a distinct session ID for this build step if caching globally
        session_id = "context_build_session"

        async def _fetch_guest(name: str) -> GuestData | None:
            try:
                profile = await service.get_fresh_profile(
                    session_id=session_id, guest_name=name, company_name=company_name
                )
                return GuestData(
                    full_name=profile.full_name,
                    position=profile.current_position,
                    organization=profile.organization,
                    biography=profile.professional_biography,
                    expertise=tuple(profile.areas_of_expertise),
                    confidence=str(profile.confidence_level),
                )
            except Exception as e:
                logger.error("Failed to load guest profile for %s: %s", name, e)
                return GuestData(
                    full_name=name,
                    biography="",
                    confidence="LOW",
                )

        tasks = [_fetch_guest(name) for name in guest_names]
        results = await asyncio.gather(*tasks)
        return [g for g in results if g is not None]

    async def _load_approved_plan(self, campaign_id: UUID | None):
        """Load the approved plan for a campaign, or None.

        A missing plan or any read error MUST NOT block generation so that
        campaigns without a plan (legacy path) continue to work.

        Args:
            campaign_id: Campaign to load the plan for, or None.

        Returns:
            An approved CampaignPlan, or None.
        """
        if campaign_id is None:
            return None

        try:
            from src.modules.planning.models.campaign_plan import CampaignPlan
            from src.modules.planning.repositories.plan_repository import PlanRepository

            repo = PlanRepository()

            plan_row = await repo.get_plan_row(campaign_id)
            if not plan_row:
                return None

            version_num = plan_row.get("current_version", 0)
            if not version_num:
                return None

            plan_version = await repo.get_version(plan_row["id"], version_num)

            if not plan_version:
                return None

            plan = CampaignPlan.from_document(plan_version.document)
            # Only attach if the plan is actually approved.
            if not plan.approved:
                logger.info("Plan for campaign %s exists but is not approved", campaign_id)
                return plan  # Return anyway so the gate node can surface the right error.

            logger.info("Loaded approved plan v%d for campaign %s", version_num, campaign_id)
            return plan

        except Exception as e:  # noqa: BLE001 - plan is optional
            logger.warning(
                "Could not load plan for campaign %s (%s); continuing without", campaign_id, e
            )
            return None

    def _get_brand_service(self) -> SupabaseService | None:
        """Return the brand data service, constructing it lazily.

        Returns:
            A SupabaseService, or None if it cannot be constructed
            (e.g. missing configuration) — brand data is optional.
        """
        if self._brand_service is None:
            try:
                self._brand_service = SupabaseService()
            except Exception as e:  # noqa: BLE001 - brand data is optional
                logger.warning("Could not initialize brand service (%s)", e)
                return None
        return self._brand_service

    def _get_guest_service(self):
        """Return the guest profile service, constructing it lazily."""
        if self._guest_profile_service is None:
            try:
                from src.cache import session_cache
                from src.config.settings import settings
                from src.services.guest_profile_service import GuestProfileService
                from src.services.guest_research import ExaGuestResearchProvider
                from src.services.llm_service import LLMService

                if not settings.exa_api_key:
                    logger.warning("EXA_API_KEY is not set. Guest research will fail.")

                provider = ExaGuestResearchProvider(api_key=settings.exa_api_key)
                llm = LLMService()
                self._guest_profile_service = GuestProfileService(
                    research_provider=provider, llm_service=llm, cache=session_cache
                )
            except Exception as e:
                logger.warning("Could not initialize guest profile service (%s)", e)
                return None
        return self._guest_profile_service
