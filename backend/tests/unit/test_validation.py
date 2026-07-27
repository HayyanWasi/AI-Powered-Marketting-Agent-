import pytest
from pydantic import ValidationError
from src.models.company import CompanyProfileCreate, CompanyProfileUpdate, CompanyProfile


class TestCompanyProfileCreate:
    def test_valid_profile(self) -> None:
        data = CompanyProfileCreate(
            company_name="Acme Corp", brand_guidelines="Use blue", brand_tone="Professional"
        )
        assert data.company_name == "Acme Corp"
        assert data.brand_guidelines == "Use blue"
        assert data.brand_tone == "Professional"

    def test_empty_name_fails(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(
                company_name="", brand_guidelines="guidelines", brand_tone="Professional"
            )

    def test_empty_guidelines_fails(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(
                company_name="Acme Corp", brand_guidelines="", brand_tone="Professional"
            )

    def test_empty_tone_fails(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(
                company_name="Acme Corp", brand_guidelines="guidelines", brand_tone=""
            )

    def test_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(
                company_name="A" * 300, brand_guidelines="guidelines", brand_tone="Professional"
            )

    def test_tone_too_long(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(
                company_name="Acme Corp", brand_guidelines="guidelines", brand_tone="T" * 2000
            )


class TestCompanyProfileUpdate:
    def test_partial_update_name(self) -> None:
        data = CompanyProfileUpdate(company_name="New Name")
        assert data.company_name == "New Name"
        assert data.brand_tone is None

    def test_partial_update_tone(self) -> None:
        data = CompanyProfileUpdate(brand_tone="New Tone")
        assert data.brand_tone == "New Tone"
        assert data.company_name is None

    def test_empty_update(self) -> None:
        data = CompanyProfileUpdate()
        assert data.company_name is None
        assert data.brand_tone is None


class TestCompanyProfileDataclass:
    def test_default_fields(self) -> None:
        profile = CompanyProfile(company_name="", brand_guidelines="")
        assert profile.company_name == ""
        assert profile.brand_guidelines == ""
        assert profile.reference_image_urls == []
        assert profile.id is not None
        assert profile.created_at is not None

    def test_custom_fields(self) -> None:
        profile = CompanyProfile(
            company_name="Acme",
            brand_guidelines="Blue tone",
            brand_tone="Pro",
            reference_image_urls=["https://img.com/1"],
        )
        assert profile.company_name == "Acme"
        assert profile.brand_guidelines == "Blue tone"
        assert profile.brand_tone == "Pro"
        assert profile.reference_image_urls == ["https://img.com/1"]

    def test_to_response(self) -> None:
        profile = CompanyProfile(
            company_name="Acme", brand_guidelines="guidelines", brand_tone="Pro"
        )
        response = profile.to_response()
        assert response.company_name == "Acme"
        assert response.brand_guidelines == "guidelines"
        assert response.brand_tone == "Pro"
