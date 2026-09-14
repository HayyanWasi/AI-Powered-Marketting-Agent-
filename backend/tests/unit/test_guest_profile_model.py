import pytest
from pydantic import ValidationError

from src.models.guest_profile import (
    ConfidenceLevel,
    GuestEvidence,
    GuestProfile,
    GuestSearchRequest,
    GuestSearchResponse,
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


class TestGuestEvidence:
    def test_default_values(self) -> None:
        evidence = GuestEvidence(url="https://example.com")
        assert evidence.url == "https://example.com"
        assert evidence.title == ""
        assert evidence.highlights == []

    def test_all_fields_populated(self) -> None:
        evidence = GuestEvidence(
            url="https://example.com",
            title="Test Page",
            highlights=["A test snippet"],
        )
        assert evidence.url == "https://example.com"
        assert evidence.title == "Test Page"
        assert evidence.highlights == ["A test snippet"]


class TestGuestProfile:
    def test_default_values(self) -> None:
        with pytest.raises(ValidationError):
            # full_name is required
            GuestProfile()

    def test_all_fields_populated(self) -> None:
        evidence = [GuestEvidence(url="https://ex.com", title="T", highlights=["S"])]
        profile = GuestProfile(
            full_name="Jane Doe",
            current_position="Engineer",
            organization="Acme",
            professional_biography="An engineer.",
            areas_of_expertise=["AI", "ML"],
            confidence_level=ConfidenceLevel.HIGH,
            evidence=evidence,
        )
        assert profile.full_name == "Jane Doe"
        assert profile.confidence_level == ConfidenceLevel.HIGH
        assert len(profile.evidence) == 1


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
        assert resp.profile is None
        assert resp.needs_manual_input is False
        assert resp.error == ""

    def test_manual_input_response(self) -> None:
        resp = GuestSearchResponse(needs_manual_input=True, error="Insufficient results")
        assert resp.needs_manual_input is True
        assert resp.error == "Insufficient results"

    def test_serialization(self) -> None:
        profile = GuestProfile(full_name="Jane", confidence_level=ConfidenceLevel.HIGH)
        resp = GuestSearchResponse(profile=profile)
        dumped = resp.model_dump()
        assert dumped["profile"]["full_name"] == "Jane"
        assert dumped["needs_manual_input"] is False
