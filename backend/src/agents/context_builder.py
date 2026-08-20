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
from src.services.search import GuestSearchService, SearchError
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
        guest_search_service: GuestSearchService | None = None,
    ) -> None:
        """Initialize the builder with the services it reads from.

        Args:
            supabase_service: Source of company brand data. Constructed lazily
                on first use if not provided (keeps tests offline-friendly).
            guest_search_service: Source of guest/speaker data.
        """
        self._brand_service = supabase_service
        self._guest_service = guest_search_service

    def build(
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
                is loaded and attached to the context so the generation
                pipeline uses the marketer-approved strategy.

        Returns:
            An immutable GenerationContext snapshot.
        """
        logger.info("Building GenerationContext for event: %s", event_name)

        brand = self._load_brand_data(company_profile_id)
        guests = self._load_guest_data(guest_names or [], brand.company_name)
        plan = self._load_approved_plan(campaign_id)

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

    def _load_guest_data(self, guest_names: list[str], company_name: str) -> list[GuestData]:
        """Research and snapshot guest/speaker data.

        A failure researching one guest MUST NOT abort the build; that guest
        is logged and skipped so the remaining guests still snapshot.

        Args:
            guest_names: Names of guests/speakers to research.
            company_name: Company context to disambiguate the search.

        Returns:
            A list of GuestData snapshots (may be shorter than the input).
        """
        if not guest_names:
            return []

        service = self._get_guest_service()
        if service is None:
            return []

        guests: list[GuestData] = []
        for name in guest_names:
            try:
                results = service.search(name, company_name or None)
            except SearchError as e:
                logger.warning("Guest search failed for '%s' (%s); skipping", name, e)
                continue

            biography = self._summarize_search(results)
            guests.append(
                GuestData(
                    full_name=name,
                    biography=biography,
                    confidence="MEDIUM" if results else "LOW",
                )
            )

        return guests

    @staticmethod
    def _summarize_search(results: list[dict]) -> str:
        """Condense raw search results into a short biography context.

        Args:
            results: Raw DuckDuckGo result dicts.

        Returns:
            A newline-joined summary of the top result snippets.
        """
        snippets = []
        for result in results[:_MAX_GUEST_SNIPPETS]:
            body = (result.get("body") or "").strip()
            if body:
                snippets.append(body)
        return "\n".join(snippets)

    def _load_approved_plan(self, campaign_id: UUID | None):
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
            import asyncio

            from src.modules.planning.models.campaign_plan import CampaignPlan
            from src.modules.planning.repositories.plan_repository import PlanRepository

            repo = PlanRepository()
            # PlanRepository methods are declared async; run them synchronously
            # here because ContextBuilder.build() is a sync method called before
            # the async event loop starts running workflow nodes.
            loop = asyncio.new_event_loop()
            try:
                plan_row = loop.run_until_complete(repo.get_plan_row(campaign_id))
            finally:
                loop.close()

            if not plan_row:
                return None

            version_num = plan_row.get("current_version", 0)
            if not version_num:
                return None

            loop2 = asyncio.new_event_loop()
            try:
                plan_version = loop2.run_until_complete(
                    repo.get_version(plan_row["id"], version_num)
                )
            finally:
                loop2.close()

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
            logger.warning("Could not load plan for campaign %s (%s); continuing without", campaign_id, e)
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

    def _get_guest_service(self) -> GuestSearchService | None:
        """Return the guest search service, constructing it lazily.

        Returns:
            A GuestSearchService, or None if it cannot be constructed
            — guest data is optional.
        """
        if self._guest_service is None:
            try:
                self._guest_service = GuestSearchService()
            except Exception as e:  # noqa: BLE001 - guest data is optional
                logger.warning("Could not initialize guest service (%s)", e)
                return None
        return self._guest_service
