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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/guest", tags=["guest"])
search_service = GuestSearchService()
llm_service = LLMService()


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

    return GuestSearchResponse(profile=profile.to_response(), needs_manual_input=False)
