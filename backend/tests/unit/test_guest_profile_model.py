import pytest
from pydantic import ValidationError

from src.models.guest_profile import (
    ConfidenceLevel,
    GuestProfile,
    GuestProfileData,
    GuestSearchRequest,
    GuestSearchResponse,
    SearchResult,
    SearchResultData,
)


class TestConfidenceLevel:
    def test_values(self) -> None:
        assert list(ConfidenceLevel) == [
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW,
        ]

    def test_string_access(self) -> None:
        assert ConfidenceLevel.HIGH.value == "HIGH"
        assert ConfidenceLevel.MEDIUM.value == "MEDIUM"
        assert ConfidenceLevel.LOW.value == "LOW"


class TestSearchResult:
    def test_default_values(self) -> None:
        result = SearchResult()
        assert result.website_name == ""
        assert result.page_title == ""
        assert result.snippet == ""
        assert result.source_url == ""

    def test_all_fields_populated(self) -> None:
        result = SearchResult(
            website_name="Example",
            page_title="Test Page",
            snippet="A test snippet",
            source_url="https://example.com",
        )
        assert result.website_name == "Example"
        assert result.page_title == "Test Page"
        assert result.snippet == "A test snippet"
        assert result.source_url == "https://example.com"

    def test_to_data(self) -> None:
        result = SearchResult(
            website_name="Ex",
            page_title="Title",
            snippet="Snippet",
            source_url="https://ex.com",
        )
        data = result.to_data()
        assert isinstance(data, SearchResultData)
        assert data.website_name == "Ex"
        assert data.page_title == "Title"


class TestSearchResultData:
    def test_defaults(self) -> None:
        data = SearchResultData()
        assert data.website_name == ""
        assert data.page_title == ""
        assert data.snippet == ""
        assert data.source_url == ""

    def test_serialization(self) -> None:
        data = SearchResultData(
            website_name="Ex",
            page_title="T",
            snippet="S",
            source_url="https://ex.com",
        )
        dumped = data.model_dump()
        assert dumped["website_name"] == "Ex"
        assert dumped["source_url"] == "https://ex.com"


class TestGuestProfile:
    def test_default_values(self) -> None:
        profile = GuestProfile()
        assert profile.full_name == ""
        assert profile.current_position == ""
        assert profile.organization == ""
        assert profile.professional_biography == ""
        assert profile.areas_of_expertise == []
        assert profile.confidence_level == ConfidenceLevel.LOW
        assert profile.sources_used == []

    def test_all_fields_populated(self) -> None:
        sources = [
            SearchResult(
                website_name="Ex", page_title="T", snippet="S", source_url="https://ex.com"
            )
        ]
        profile = GuestProfile(
            full_name="Jane Doe",
            current_position="Engineer",
            organization="Acme",
            professional_biography="An engineer.",
            areas_of_expertise=["AI", "ML"],
            confidence_level=ConfidenceLevel.HIGH,
            sources_used=sources,
        )
        assert profile.full_name == "Jane Doe"
        assert profile.confidence_level == ConfidenceLevel.HIGH
        assert len(profile.sources_used) == 1

    def test_to_response(self) -> None:
        sources = [
            SearchResult(
                website_name="Ex", page_title="T", snippet="S", source_url="https://ex.com"
            )
        ]
        profile = GuestProfile(
            full_name="Jane Doe",
            current_position="Engineer",
            organization="Acme",
            professional_biography="Bio.",
            areas_of_expertise=["AI"],
            confidence_level=ConfidenceLevel.MEDIUM,
            sources_used=sources,
        )
        response = profile.to_response()
        assert isinstance(response, GuestProfileData)
        assert response.full_name == "Jane Doe"
        assert response.confidence_level == ConfidenceLevel.MEDIUM
        assert len(response.sources_used) == 1
        assert response.sources_used[0].website_name == "Ex"

    def test_to_response_empty(self) -> None:
        profile = GuestProfile()
        response = profile.to_response()
        assert response.full_name == ""
        assert response.confidence_level == ConfidenceLevel.LOW
        assert response.sources_used == []


class TestGuestSearchRequest:
    def test_valid_request(self) -> None:
        req = GuestSearchRequest(guest_name="Jane Doe")
        assert req.guest_name == "Jane Doe"
        assert req.company_name is None
        assert req.session_id is None

    def test_with_optional_fields(self) -> None:
        req = GuestSearchRequest(guest_name="Jane Doe", company_name="Acme", session_id="sess-123")
        assert req.company_name == "Acme"
        assert req.session_id == "sess-123"

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GuestSearchRequest(guest_name="")


class TestGuestSearchResponse:
    def test_default_response(self) -> None:
        resp = GuestSearchResponse()
        assert isinstance(resp.profile, GuestProfileData)
        assert resp.profile.full_name == ""
        assert resp.needs_manual_input is False
        assert resp.error == ""

    def test_manual_input_response(self) -> None:
        resp = GuestSearchResponse(needs_manual_input=True, error="Insufficient results")
        assert resp.needs_manual_input is True
        assert resp.error == "Insufficient results"

    def test_serialization(self) -> None:
        profile = GuestProfileData(full_name="Jane", confidence_level=ConfidenceLevel.HIGH)
        resp = GuestSearchResponse(profile=profile)
        dumped = resp.model_dump()
        assert dumped["profile"]["full_name"] == "Jane"
        assert dumped["needs_manual_input"] is False
