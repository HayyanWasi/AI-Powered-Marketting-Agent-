from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

VALID_PROFILE_ID = "550e8400-e29b-41d4-a716-446655440000"


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

        mock_svc = MagicMock()
        mock_svc.execute.return_value = mock_profile

        with patch("src.api.v1.company.CreateCompanyService", return_value=mock_svc):
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
        mock_svc = MagicMock()
        mock_svc.execute.side_effect = ValueError("Company name 'Duplicate' already exists")

        with patch("src.api.v1.company.CreateCompanyService", return_value=mock_svc):
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
        mock_svc = MagicMock()
        mock_svc.execute.return_value = {
            "id": VALID_PROFILE_ID,
            "company_name": "Acme",
            "brand_guidelines": "guidelines",
            "brand_tone": "Pro",
            "reference_image_urls": [],
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
            "is_complete": True,
        }

        with patch("src.api.v1.company.GetCompanyService", return_value=mock_svc):
            response = client.get(f"/api/company/{VALID_PROFILE_ID}")
            assert response.status_code == 200
            assert response.json()["id"] == VALID_PROFILE_ID

    def test_get_company_not_found(self) -> None:
        mock_svc = MagicMock()
        mock_svc.execute.side_effect = ValueError("Company profile not found")

        with patch("src.api.v1.company.GetCompanyService", return_value=mock_svc):
            response = client.get(f"/api/company/{VALID_PROFILE_ID}")
            assert response.status_code == 404

    def test_get_company_invalid_id(self) -> None:
        response = client.get("/api/company/not-a-uuid")
        assert response.status_code == 422


class TestUpdateCompanyAPI:
    def test_update_company_success(self) -> None:
        mock_profile = type(
            "Profile",
            (),
            {
                "id": VALID_PROFILE_ID,
                "company_name": "Updated",
                "brand_guidelines": "updated",
                "brand_tone": "Casual",
                "reference_image_urls": [],
                "created_at": "2026-01-01",
                "updated_at": "2026-01-02",
            },
        )()

        mock_svc = MagicMock()
        mock_svc.execute.return_value = mock_profile

        with patch("src.api.v1.company.UpdateCompanyService", return_value=mock_svc):
            response = client.put(
                f"/api/company/{VALID_PROFILE_ID}",
                json={"company_name": "Updated", "brand_tone": "Casual"},
            )
            assert response.status_code == 200
            assert response.json()["company_name"] == "Updated"

    def test_update_company_not_found(self) -> None:
        mock_svc = MagicMock()
        mock_svc.execute.side_effect = ValueError("Company profile not found")

        with patch("src.api.v1.company.UpdateCompanyService", return_value=mock_svc):
            response = client.put(
                f"/api/company/{VALID_PROFILE_ID}",
                json={"company_name": "X"},
            )
            assert response.status_code == 404

    def test_update_company_no_fields(self) -> None:
        response = client.put(f"/api/company/{VALID_PROFILE_ID}", json={})
        assert response.status_code == 422


class TestDeleteCompanyAPI:
    def test_delete_company_success(self) -> None:
        mock_svc = MagicMock()
        mock_svc.execute.return_value = None

        with patch("src.api.v1.company.DeleteCompanyService", return_value=mock_svc):
            response = client.delete(f"/api/company/{VALID_PROFILE_ID}")
            assert response.status_code == 204

    def test_delete_company_not_found(self) -> None:
        mock_svc = MagicMock()
        mock_svc.execute.side_effect = ValueError("Company profile not found")

        with patch("src.api.v1.company.DeleteCompanyService", return_value=mock_svc):
            response = client.delete(f"/api/company/{VALID_PROFILE_ID}")
            assert response.status_code == 404
