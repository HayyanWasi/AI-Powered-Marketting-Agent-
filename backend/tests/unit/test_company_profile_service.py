from unittest.mock import MagicMock

import pytest

from src.models.errors import ErrorCode
from src.services.company_profile_service import (
    CompanyProfileNotFoundError,
    CompanyProfileService,
    CompanyProfileServiceError,
)
from src.services.supabase import NotFoundError, SupabaseServiceError


@pytest.fixture
def mock_supabase() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(mock_supabase: MagicMock) -> CompanyProfileService:
    return CompanyProfileService(supabase_service=mock_supabase)


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_profile_found(
        self, service: CompanyProfileService, mock_supabase: MagicMock
    ) -> None:
        mock_supabase.get_profile.return_value = {
            "id": "test-id",
            "name": "Test Corp",
            "brand_colors": ["#FF0000"],
            "brand_personality": "bold",
            "style_guide": "modern",
            "logo_url": "https://example.com/logo.png",
            "typography_style": "sans-serif",
            "reference_image_urls": ["https://example.com/ref.jpg"],
            "industry_category": "tech",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-02",
        }

        profile = await service.get_profile("test-id")

        assert profile.id == "test-id"
        assert profile.name == "Test Corp"
        assert profile.brand_colors == ["#FF0000"]
        assert profile.brand_personality == "bold"
        assert profile.logo_url == "https://example.com/logo.png"

    @pytest.mark.asyncio
    async def test_profile_not_found(
        self, service: CompanyProfileService, mock_supabase: MagicMock
    ) -> None:
        mock_supabase.get_profile.side_effect = NotFoundError("Profile not found")

        with pytest.raises(CompanyProfileNotFoundError) as exc_info:
            await service.get_profile("nonexistent-id")

        assert exc_info.value.error_code == ErrorCode.PROFILE_NOT_FOUND
        assert exc_info.value.details == {"profile_id": "nonexistent-id"}

    @pytest.mark.asyncio
    async def test_supabase_error(
        self, service: CompanyProfileService, mock_supabase: MagicMock
    ) -> None:
        mock_supabase.get_profile.side_effect = SupabaseServiceError("DB connection failed")

        with pytest.raises(CompanyProfileServiceError) as exc_info:
            await service.get_profile("test-id")

        assert exc_info.value.error_code == ErrorCode.INTERNAL_ERROR

    @pytest.mark.asyncio
    async def test_profile_with_optional_fields_missing(
        self, service: CompanyProfileService, mock_supabase: MagicMock
    ) -> None:
        mock_supabase.get_profile.return_value = {
            "id": "minimal-id",
            "name": "Minimal Corp",
        }

        profile = await service.get_profile("minimal-id")

        assert profile.id == "minimal-id"
        assert profile.brand_colors is None
        assert profile.brand_personality is None
        assert profile.logo_url is None
