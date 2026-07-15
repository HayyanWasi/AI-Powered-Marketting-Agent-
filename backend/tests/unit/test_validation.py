import pytest
from pydantic import ValidationError
from src.models.company import CompanyProfileCreate, CompanyProfileUpdate, CompanyProfile


class TestCompanyProfileCreate:
    def test_valid_profile(self) -> None:
        data = CompanyProfileCreate(name="Acme Corp", tone="Professional")
        assert data.name == "Acme Corp"
        assert data.tone == "Professional"

    def test_empty_name_fails(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(name="", tone="Professional")

    def test_empty_tone_fails(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(name="Acme Corp", tone="")

    def test_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(name="A" * 300, tone="Professional")

    def test_tone_too_long(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(name="Acme Corp", tone="T" * 2000)


class TestCompanyProfileUpdate:
    def test_partial_update_name(self) -> None:
        data = CompanyProfileUpdate(name="New Name")
        assert data.name == "New Name"
        assert data.tone is None

    def test_partial_update_tone(self) -> None:
        data = CompanyProfileUpdate(tone="New Tone")
        assert data.tone == "New Tone"
        assert data.name is None

    def test_empty_update(self) -> None:
        data = CompanyProfileUpdate()
        assert data.name is None
        assert data.tone is None


class TestCompanyProfileDataclass:
    def test_default_fields(self) -> None:
        profile = CompanyProfile()
        assert profile.name == ""
        assert profile.tone == ""
        assert profile.reference_image_urls == []
        assert profile.id is not None
        assert profile.created_at is not None

    def test_custom_fields(self) -> None:
        profile = CompanyProfile(
            name="Acme", tone="Pro", reference_image_urls=["https://img.com/1"]
        )
        assert profile.name == "Acme"
        assert profile.tone == "Pro"
        assert profile.reference_image_urls == ["https://img.com/1"]

    def test_to_response(self) -> None:
        profile = CompanyProfile(name="Acme", tone="Pro")
        response = profile.to_response()
        assert response.name == "Acme"
        assert response.tone == "Pro"
