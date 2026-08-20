import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from src.models.guest_profile import (
    GuestProfile,
    GuestSearchRequest,
    GuestSearchResponse,
    SearchResult,
)
from src.services.llm import LLMError, LLMService
from src.services.search import GuestSearchService, SearchError
from src.services.supabase import SupabaseService, SupabaseServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/guest", tags=["guest"])
search_service = GuestSearchService()
llm_service = LLMService()
supabase_service = SupabaseService()


def _save_guest_profile(profile: GuestProfile) -> None:
    """Save guest profile to the database.

    Uses upsert to handle duplicate profiles (same name + organization).
    """
    try:
        client = supabase_service.client

        # Prepare sources as JSON
        sources_json = []
        for source in profile.sources_used:
            sources_json.append(
                {
                    "website_name": source.website_name,
                    "page_title": source.page_title,
                    "snippet": source.snippet,
                    "source_url": source.source_url,
                }
            )

        # Upsert guest profile
        row = {
            "full_name": profile.full_name,
            "current_position": profile.current_position,
            "organization": profile.organization,
            "professional_biography": profile.professional_biography,
            "areas_of_expertise": profile.areas_of_expertise,
            "confidence_level": (
                profile.confidence_level.value
                if hasattr(profile.confidence_level, "value")
                else str(profile.confidence_level)
            ),
            "sources": sources_json,
        }

        # Use upsert to insert or update
        result = (
            client.table("guest_profiles")
            .upsert(row, on_conflict="full_name,organization")
            .execute()
        )

        if result.data:
            logger.info("Guest profile saved: %s", profile.full_name)
        else:
            logger.warning("Guest profile upsert returned no data")

    except SupabaseServiceError as e:
        logger.warning("Supabase error saving guest profile: %s", e)
        raise
    except Exception as e:
        logger.warning("Unexpected error saving guest profile: %s", e)
        raise


def _build_search_results(raw_results: list[dict[str, Any]]) -> list[SearchResult]:
    return [
        SearchResult(
            website_name=_extract_website_name(r.get("href", "")),
            page_title=r.get("title", ""),
            snippet=r.get("body", ""),
            source_url=r.get("href", ""),
        )
        for r in raw_results
    ]


def _extract_website_name(url: str) -> str:
    if not url:
        return ""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname.removeprefix("www.")
    except Exception:
        return ""


@router.post("/search")
async def search_guest(body: GuestSearchRequest) -> GuestSearchResponse:
    try:
        raw_results = search_service.search(body.guest_name, company_name=body.company_name)
    except SearchError as e:
        logger.error("Search failed for '%s': %s", body.guest_name, e)
        raise HTTPException(status_code=502, detail=f"Search service error: {e}")

    if not raw_results:
        logger.info("No search results for '%s'; requesting manual input", body.guest_name)
        return GuestSearchResponse(
            needs_manual_input=True,
            error="No search results found. Please provide the guest's biography, position, and organization manually.",
        )

    search_results = _build_search_results(raw_results)

    try:
        profile_data = llm_service.analyze_search_results(raw_results)
    except LLMError as e:
        logger.error("LLM analysis failed for '%s': %s", body.guest_name, e)
        raise HTTPException(status_code=502, detail=f"Analysis service error: {e}")

    profile = GuestProfile(
        full_name=profile_data.full_name,
        current_position=profile_data.current_position,
        organization=profile_data.organization,
        professional_biography=profile_data.professional_biography,
        areas_of_expertise=list(profile_data.areas_of_expertise),
        confidence_level=profile_data.confidence_level,
        sources_used=search_results,
    )

    if not profile.full_name and not profile.current_position and not profile.organization:
        logger.info(
            "LLM could not extract profile for '%s'; requesting manual input", body.guest_name
        )
        return GuestSearchResponse(
            needs_manual_input=True,
            error="Could not generate a reliable profile. Please provide the guest's biography, position, and organization manually.",
        )

    # Persist guest profile to database
    try:
        _save_guest_profile(profile)
        logger.info("Saved guest profile for '%s' to database", profile.full_name)
    except Exception as e:
        logger.warning("Failed to save guest profile to database: %s", e)
        # Continue anyway - profile is still returned to caller

    return GuestSearchResponse(profile=profile.to_response(), needs_manual_input=False)
