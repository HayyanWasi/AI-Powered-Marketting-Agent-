from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestCreateCompanyAPI:
    def test_create_company_success(self) -> None:
        mock_profile = type(
            "Profile",
            (),
            {
                "id": "123",
                "company_name": "Acme",
                "brand_guidelines": "guidelines",
                "brand_tone": "Pro",
                "reference_image_urls": [],
                "created_at": "2026-01-01",
                "updated_at": "2026-01-01",
            },
        )()

        with patch("src.api.routes.company.create_service.execute") as mock_exec:
            mock_exec.return_value = mock_profile
            response = client.post(
                "/api/company",
                json={
                    "company_name": "Acme",
                    "brand_guidelines": "guidelines",
                    "brand_tone": "Pro",
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == "123"
            assert data["company_name"] == "Acme"

    def test_create_company_duplicate(self) -> None:
        with patch("src.api.routes.company.create_service.execute") as mock_exec:
            mock_exec.side_effect = ValueError("Company name 'Duplicate' already exists")
            response = client.post(
                "/api/company",
                json={"company_name": "Duplicate", "brand_guidelines": "guidelines"},
            )
            assert response.status_code == 409

    def test_create_company_missing_fields(self) -> None:
        response = client.post("/api/company", json={})
        assert response.status_code == 422


class TestGetCompanyAPI:
    def test_get_company_success(self) -> None:
        with patch("src.api.routes.company.get_service.execute") as mock_exec:
            mock_exec.return_value = {
                "id": "123",
                "company_name": "Acme",
                "brand_guidelines": "guidelines",
                "brand_tone": "Pro",
                "reference_image_urls": [],
                "created_at": "2026-01-01",
                "updated_at": "2026-01-01",
                "is_complete": True,
            }
            response = client.get("/api/company/123")
            assert response.status_code == 200
            assert response.json()["id"] == "123"

    def test_get_company_not_found(self) -> None:
        with patch("src.api.routes.company.get_service.execute") as mock_exec:
            mock_exec.side_effect = ValueError("Company profile not found")
            response = client.get("/api/company/nonexistent")
            assert response.status_code == 404


class TestUpdateCompanyAPI:
    def test_update_company_success(self) -> None:
        mock_profile = type(
            "Profile",
            (),
            {
                "id": "123",
                "company_name": "Updated",
                "brand_guidelines": "guidelines",
                "brand_tone": "Pro",
                "reference_image_urls": [],
                "created_at": "2026-01-01",
                "updated_at": "2026-01-01",
            },
        )()

        with patch("src.api.routes.company.update_service.execute") as mock_exec:
            mock_exec.return_value = mock_profile
            response = client.put("/api/company/123", json={"company_name": "Updated"})
            assert response.status_code == 200
            assert response.json()["company_name"] == "Updated"

    def test_update_company_not_found(self) -> None:
        with patch("src.api.routes.company.update_service.execute") as mock_exec:
            mock_exec.side_effect = ValueError("Company profile not found")
            response = client.put("/api/company/nonexistent", json={"company_name": "X"})
            assert response.status_code == 404

    def test_update_company_no_fields(self) -> None:
        response = client.put("/api/company/123", json={})
        assert response.status_code == 422


class TestDeleteCompanyAPI:
    def test_delete_company_success(self) -> None:
        with patch("src.api.routes.company.delete_service.execute") as mock_exec:
            mock_exec.return_value = None
            response = client.delete("/api/company/123")
            assert response.status_code == 204

    def test_delete_company_not_found(self) -> None:
        with patch("src.api.routes.company.delete_service.execute") as mock_exec:
            mock_exec.side_effect = ValueError("Company profile not found")
            response = client.delete("/api/company/nonexistent")
            assert response.status_code == 404
