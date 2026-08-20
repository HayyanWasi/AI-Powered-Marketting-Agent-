"""Tests for the agents ContextBuilder (brand + guest loading).

External services (Supabase, guest search) are mocked per constitution
§Test-First — no network calls.
"""

from unittest.mock import MagicMock

from src.agents.context_builder import ContextBuilder
from src.services.search import SearchError
from src.services.supabase import NotFoundError, SupabaseServiceError


def _brand_service(row: dict) -> MagicMock:
    service = MagicMock()
    service.get_profile.return_value = row
    return service


class TestBrandLoading:
    def test_maps_db_row_to_brand_data(self) -> None:
        row = {
            "company_name": "Acme Corp",
            "brand_guidelines": "Clean, minimal",
            "brand_tone": "Confident",
            "reference_image_urls": ["https://img/1.png", "https://img/2.png"],
        }
        builder = ContextBuilder(supabase_service=_brand_service(row))

        ctx = builder.build(company_profile_id="prof-1")

        assert ctx.brand.company_name == "Acme Corp"
        assert ctx.brand.brand_guidelines == "Clean, minimal"
        assert ctx.brand.brand_tone == "Confident"
        assert ctx.brand.reference_image_urls == (
            "https://img/1.png",
            "https://img/2.png",
        )
        assert ctx.brand.style_guide == "Clean, minimal"

    def test_no_profile_id_yields_empty_brand(self) -> None:
        service = MagicMock()
        builder = ContextBuilder(supabase_service=service)

        ctx = builder.build()

        assert ctx.brand.company_name == ""
        service.get_profile.assert_not_called()

    def test_missing_profile_does_not_raise(self) -> None:
        service = MagicMock()
        service.get_profile.side_effect = NotFoundError("nope")
        builder = ContextBuilder(supabase_service=service)

        ctx = builder.build(company_profile_id="ghost")

        assert ctx.brand.company_name == ""

    def test_service_error_does_not_raise(self) -> None:
        service = MagicMock()
        service.get_profile.side_effect = SupabaseServiceError("boom")
        builder = ContextBuilder(supabase_service=service)

        ctx = builder.build(company_profile_id="prof-1")

        assert ctx.brand.company_name == ""

    def test_null_reference_urls_normalized_to_empty_tuple(self) -> None:
        row = {"company_name": "Acme", "reference_image_urls": None}
        builder = ContextBuilder(supabase_service=_brand_service(row))

        ctx = builder.build(company_profile_id="prof-1")

        assert ctx.brand.reference_image_urls == ()


class TestGuestLoading:
    def test_maps_search_results_to_guest_data(self) -> None:
        search = MagicMock()
        search.search.return_value = [
            {"body": "Jane is an AI researcher."},
            {"body": "Jane spoke at the summit."},
        ]
        builder = ContextBuilder(
            supabase_service=_brand_service({"company_name": "Acme"}),
            guest_search_service=search,
        )

        ctx = builder.build(company_profile_id="prof-1", guest_names=["Jane Doe"])

        assert len(ctx.guests) == 1
        guest = ctx.guests[0]
        assert guest.full_name == "Jane Doe"
        assert "AI researcher" in guest.biography
        assert guest.confidence == "MEDIUM"
        search.search.assert_called_once_with("Jane Doe", "Acme")

    def test_one_guest_failure_is_skipped(self) -> None:
        search = MagicMock()
        search.search.side_effect = [
            SearchError("rate limited"),
            [{"body": "Bob is an engineer."}],
        ]
        builder = ContextBuilder(
            supabase_service=_brand_service({"company_name": "Acme"}),
            guest_search_service=search,
        )

        ctx = builder.build(company_profile_id="prof-1", guest_names=["Jane Doe", "Bob Smith"])

        assert [g.full_name for g in ctx.guests] == ["Bob Smith"]

    def test_no_guests_yields_empty_tuple(self) -> None:
        search = MagicMock()
        builder = ContextBuilder(guest_search_service=search)

        ctx = builder.build()

        assert ctx.guests == ()
        search.search.assert_not_called()

    def test_empty_results_gives_low_confidence(self) -> None:
        search = MagicMock()
        search.search.return_value = []
        builder = ContextBuilder(
            supabase_service=_brand_service({"company_name": "Acme"}),
            guest_search_service=search,
        )

        ctx = builder.build(company_profile_id="prof-1", guest_names=["Nobody"])

        assert ctx.guests[0].confidence == "LOW"
        assert ctx.guests[0].biography == ""


class TestEventData:
    def test_event_fields_snapshot(self) -> None:
        builder = ContextBuilder(supabase_service=MagicMock())

        ctx = builder.build(
            event_name="AI Summit",
            event_date="2026-07-25",
            venue="Expo Center",
            platforms=["linkedin", "instagram"],
            registration_link="https://reg",
        )

        assert ctx.event.event_name == "AI Summit"
        assert ctx.event.event_date == "2026-07-25"
        assert ctx.event.venue == "Expo Center"
        assert ctx.event.platforms == ("linkedin", "instagram")
        assert ctx.event.registration_link == "https://reg"
