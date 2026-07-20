from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.services.supabase import (
    DuplicateCompanyError,
    NotFoundError,
    RetryExhaustedError,
    SupabaseService,
    ValidationError,
    MAX_IMAGE_SIZE,
)


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_table(mock_client: MagicMock) -> MagicMock:
    table = MagicMock()
    mock_client.table.return_value = table
    return table


@pytest.fixture
def service(mock_client: MagicMock) -> SupabaseService:
    return SupabaseService(client=mock_client)


class TestCreateProfile:
    def test_create_profile_success(self, service: SupabaseService, mock_table: MagicMock) -> None:
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []
        mock_table.insert.return_value.execute.return_value.data = [
            {"id": "123", "company_name": "Acme"}
        ]

        result = service.create_profile("Acme", "Guidelines", "Pro")
        assert result["id"] == "123"
        assert result["company_name"] == "Acme"

    def test_create_profile_duplicate(
        self, service: SupabaseService, mock_table: MagicMock
    ) -> None:
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "existing"}
        ]

        with pytest.raises(DuplicateCompanyError):
            service.create_profile("Acme", "Guidelines", "Pro")

    def test_create_profile_retry_then_fail(
        self, service: SupabaseService, mock_table: MagicMock
    ) -> None:
        mock_table.select.side_effect = Exception("Network error")

        with pytest.raises(RetryExhaustedError):
            service.create_profile("Acme", "Pro")


class TestGetProfile:
    def test_get_profile_success(self, service: SupabaseService, mock_table: MagicMock) -> None:
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [{"id": "123"}]

        result = service.get_profile("123")
        assert result["id"] == "123"

    def test_get_profile_not_found(self, service: SupabaseService, mock_table: MagicMock) -> None:
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(NotFoundError):
            service.get_profile("nonexistent")


class TestUpdateProfile:
    def test_update_profile_success(self, service: SupabaseService, mock_table: MagicMock) -> None:
        mock_table.select.return_value.eq.return_value.neq.return_value.execute.return_value.data = (
            []
        )
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": "123", "company_name": "Updated"}
        ]

        result = service.update_profile("123", {"company_name": "Updated"})
        assert result["company_name"] == "Updated"

    def test_update_profile_not_found(
        self, service: SupabaseService, mock_table: MagicMock
    ) -> None:
        mock_table.select.return_value.eq.return_value.neq.return_value.execute.return_value.data = (
            []
        )
        mock_table.update.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(NotFoundError):
            service.update_profile("nonexistent", {"company_name": "X"})


class TestDeleteProfile:
    def test_delete_profile_success(self, service: SupabaseService, mock_table: MagicMock) -> None:
        mock_table.delete.return_value.eq.return_value.execute.return_value.data = [{"id": "123"}]

        service.delete_profile("123")

    def test_delete_profile_not_found(
        self, service: SupabaseService, mock_table: MagicMock
    ) -> None:
        mock_table.delete.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(NotFoundError):
            service.delete_profile("nonexistent")


class TestUploadImage:
    def test_upload_image_success(
        self, service: SupabaseService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        img_file = tmp_path / "test.png"
        img_file.write_text("fake image content")
        mock_client.storage.from_.return_value.upload.return_value = None
        mock_client.storage.from_.return_value.get_public_url.return_value = (
            "https://img.com/test.png"
        )

        url = service.upload_image(img_file, "image/png")
        assert url == "https://img.com/test.png"

    def test_upload_image_unsupported_format(
        self, service: SupabaseService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        img_file = tmp_path / "test.gif"
        img_file.write_text("fake gif")

        with pytest.raises(ValidationError, match="Unsupported format"):
            service.upload_image(img_file, "image/gif")

    def test_upload_image_too_large(
        self, service: SupabaseService, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        img_file = tmp_path / "large.png"
        img_file.write_bytes(b"x" * (MAX_IMAGE_SIZE + 1))

        with pytest.raises(ValidationError, match="File too large"):
            service.upload_image(img_file, "image/png")
