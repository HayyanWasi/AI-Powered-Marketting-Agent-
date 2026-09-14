import logging
from typing import Any

from fastapi import APIRouter

from src.models.guest_profile import (
    GuestEvidence,
    GuestProfile,
    GuestSearchRequest,
    GuestSearchResponse,
)
from src.services.supabase import SupabaseService, SupabaseServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/guest", tags=["guest"])
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


def _build_search_results(raw_results: list[dict[str, Any]]) -> list[GuestEvidence]:
    return [
        GuestEvidence(
            url=r.get("href", ""),
            title=r.get("title", ""),
            highlights=[r.get("body")] if r.get("body") else [],
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
    # Legacy DDGS research removed as per V2 migration plan.
    logger.info(
        "Search endpoint called for '%s', but research implementation is removed.", body.guest_name
    )
    return GuestSearchResponse(
        needs_manual_input=True,
        error="Search implementation removed for V2. Please provide the guest's biography manually.",
    )
