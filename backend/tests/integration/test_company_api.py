from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app
from src.services.supabase import DuplicateCompanyError, NotFoundError

client = TestClient(app)


class TestCreateCompanyAPI:
    def test_create_company_success(self) -> None:
        with patch("src.api.routes.company.service.create_profile") as mock_create:
            mock_create.return_value = {
                "id": "123",
                "name": "Acme",
                "tone": "Pro",
                "reference_image_urls": [],
            }

            response = client.post("/api/company", json={"name": "Acme", "tone": "Pro"})

            assert response.status_code == 201
            data = response.json()
            assert data["id"] == "123"
            assert data["name"] == "Acme"

    def test_create_company_duplicate(self) -> None:
        with patch("src.api.routes.company.service.create_profile") as mock_create:
            mock_create.side_effect = DuplicateCompanyError("Company name already exists")

            response = client.post("/api/company", json={"name": "Duplicate", "tone": "Pro"})

            assert response.status_code == 409

    def test_create_company_missing_fields(self) -> None:
        response = client.post("/api/company", json={})
        assert response.status_code == 422


class TestGetCompanyAPI:
    def test_get_company_success(self) -> None:
        with patch("src.api.routes.company.service.get_profile") as mock_get:
            mock_get.return_value = {
                "id": "123",
                "name": "Acme",
                "tone": "Pro",
                "reference_image_urls": [],
            }

            response = client.get("/api/company/123")

            assert response.status_code == 200
            assert response.json()["id"] == "123"

    def test_get_company_not_found(self) -> None:
        with patch("src.api.routes.company.service.get_profile") as mock_get:
            mock_get.side_effect = NotFoundError("Profile not found")

            response = client.get("/api/company/nonexistent")

            assert response.status_code == 404


class TestUpdateCompanyAPI:
    def test_update_company_success(self) -> None:
        with patch("src.api.routes.company.service.update_profile") as mock_update:
            mock_update.return_value = {"id": "123", "name": "Updated", "tone": "Pro"}

            response = client.put("/api/company/123", json={"name": "Updated"})

            assert response.status_code == 200
            assert response.json()["name"] == "Updated"

    def test_update_company_not_found(self) -> None:
        with patch("src.api.routes.company.service.update_profile") as mock_update:
            mock_update.side_effect = NotFoundError("Profile not found")

            response = client.put("/api/company/nonexistent", json={"name": "X"})

            assert response.status_code == 404

    def test_update_company_no_fields(self) -> None:
        response = client.put("/api/company/123", json={})
        assert response.status_code == 422


class TestDeleteCompanyAPI:
    def test_delete_company_success(self) -> None:
        with patch("src.api.routes.company.service.delete_profile") as mock_delete:
            mock_delete.return_value = None

            response = client.delete("/api/company/123")

            assert response.status_code == 204

    def test_delete_company_not_found(self) -> None:
        with patch("src.api.routes.company.service.delete_profile") as mock_delete:
            mock_delete.side_effect = NotFoundError("Profile not found")

            response = client.delete("/api/company/nonexistent")

            assert response.status_code == 404
