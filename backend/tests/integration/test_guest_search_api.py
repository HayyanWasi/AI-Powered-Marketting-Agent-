from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestGuestSearchAPI:
    def test_search_guest_happy_path(self, mock_ddgs: MagicMock, mock_llm: MagicMock) -> None:
        with patch("src.api.v1.guest.search_service") as mock_svc:
            mock_svc.search.return_value = [
                {
                    "title": "Jane Doe - Researcher",
                    "href": "https://ex.com",
                    "body": "Jane is a researcher.",
                },
            ]
            with patch("src.api.v1.guest.llm_service") as mock_llm_svc:
                from src.models.guest_profile import (
                    GuestProfileData,
                    ConfidenceLevel,
                    SearchResultData,
                )

                mock_llm_svc.analyze_search_results.return_value = GuestProfileData(
                    full_name="Jane Doe",
                    current_position="Researcher",
                    organization="TechCorp",
                    professional_biography="Jane is a researcher at TechCorp.",
                    areas_of_expertise=["AI"],
                    confidence_level=ConfidenceLevel.HIGH,
                    sources_used=[
                        SearchResultData(
                            website_name="ex.com",
                            page_title="Jane Doe - Researcher",
                            snippet="Jane is a researcher.",
                            source_url="https://ex.com",
                        ),
                    ],
                )

                response = client.post("/api/guest/search", json={"guest_name": "Jane Doe"})
                assert response.status_code == 200
                data = response.json()
                assert data["needs_manual_input"] is False
                assert data["profile"]["full_name"] == "Jane Doe"
                assert data["profile"]["current_position"] == "Researcher"
                assert data["profile"]["confidence_level"] == "HIGH"
                assert len(data["profile"]["sources_used"]) == 1

    def test_search_guest_with_company(self, mock_ddgs: MagicMock, mock_llm: MagicMock) -> None:
        with patch("src.api.v1.guest.search_service") as mock_svc:
            mock_svc.search.return_value = [
                {"title": "Jane Doe - CEO", "href": "https://ex.com", "body": "CEO at Acme Corp."},
            ]
            with patch("src.api.v1.guest.llm_service") as mock_llm_svc:
                from src.models.guest_profile import GuestProfileData, ConfidenceLevel

                mock_llm_svc.analyze_search_results.return_value = GuestProfileData(
                    full_name="Jane Doe",
                    current_position="CEO",
                    organization="Acme Corp",
                    professional_biography="CEO at Acme Corp.",
                    areas_of_expertise=["Leadership"],
                    confidence_level=ConfidenceLevel.MEDIUM,
                    sources_used=[],
                )

                response = client.post(
                    "/api/guest/search",
                    json={"guest_name": "Jane Doe", "company_name": "Acme Corp"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["needs_manual_input"] is False
                assert data["profile"]["organization"] == "Acme Corp"

    def test_no_results_returns_manual_input(
        self, mock_ddgs: MagicMock, mock_llm: MagicMock
    ) -> None:
        with patch("src.api.v1.guest.search_service") as mock_svc:
            mock_svc.search.return_value = []

            response = client.post("/api/guest/search", json={"guest_name": "Unknown Person"})
            assert response.status_code == 200
            data = response.json()
            assert data["needs_manual_input"] is True
            assert "no search results" in data["error"].lower()

    def test_partial_profile_fallback(self, mock_ddgs: MagicMock, mock_llm: MagicMock) -> None:
        with patch("src.api.v1.guest.search_service") as mock_svc:
            mock_svc.search.return_value = [
                {"title": "Result", "href": "https://ex.com", "body": "Body"},
            ]
            with patch("src.api.v1.guest.llm_service") as mock_llm_svc:
                from src.models.guest_profile import GuestProfileData, ConfidenceLevel

                mock_llm_svc.analyze_search_results.return_value = GuestProfileData(
                    full_name="",
                    current_position="",
                    organization="",
                    professional_biography="",
                    areas_of_expertise=[],
                    confidence_level=ConfidenceLevel.LOW,
                    sources_used=[],
                )

                response = client.post("/api/guest/search", json={"guest_name": "Minimal"})
                assert response.status_code == 200
                data = response.json()
                assert data["needs_manual_input"] is True

    def test_search_service_error(self, mock_ddgs: MagicMock, mock_llm: MagicMock) -> None:
        with patch("src.api.v1.guest.search_service") as mock_svc:
            from src.services.search import SearchError

            mock_svc.search.side_effect = SearchError("Service unavailable")

            response = client.post("/api/guest/search", json={"guest_name": "Jane Doe"})
            assert response.status_code == 502
            body = response.json()
            assert "Search service error" in body.get("message", "") or "Search service error" in body.get("error", "")

    def test_invalid_input_empty_name(self) -> None:
        response = client.post("/api/guest/search", json={"guest_name": ""})
        assert response.status_code == 422

    def test_invalid_input_missing_name(self) -> None:
        response = client.post("/api/guest/search", json={})
        assert response.status_code == 422
