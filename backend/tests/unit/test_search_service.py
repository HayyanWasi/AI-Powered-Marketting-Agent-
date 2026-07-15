from unittest.mock import MagicMock

import pytest

from src.services.search import GuestSearchService, SearchError


class TestGuestSearchService:
    def test_search_returns_results(self, mock_ddgs: MagicMock) -> None:
        service = GuestSearchService(ddgs=mock_ddgs)
        results = service.search("Jane Doe")
        assert len(results) == 2
        assert results[0]["title"] == "Jane Doe - AI Researcher at TechCorp"
        assert results[0]["href"] == "https://example.com/jane-doe"
        assert (
            results[0]["body"]
            == "Jane Doe is a leading AI researcher specializing in natural language processing."
        )

    def test_search_with_company_name_retries_when_few_results(self, mock_ddgs: MagicMock) -> None:
        service = GuestSearchService(ddgs=mock_ddgs)
        results = service.search("Jane Doe", company_name="TechCorp")
        assert len(results) == 2
        assert mock_ddgs.text.call_count == 2

    def test_no_results_returns_empty_list(self, mock_ddgs_no_results: MagicMock) -> None:
        service = GuestSearchService(ddgs=mock_ddgs_no_results)
        results = service.search("Unknown Person")
        assert results == []

    def test_company_search_retries_with_name_only_when_few_results(self) -> None:
        mock = MagicMock()
        mock.text.side_effect = [
            [{"title": "R1", "href": "https://ex.com/1", "body": "Body 1"}],
            [
                {"title": "R2", "href": "https://ex.com/2", "body": "Body 2"},
                {"title": "R3", "href": "https://ex.com/3", "body": "Body 3"},
            ],
        ]
        service = GuestSearchService(ddgs=mock)
        results = service.search("Jane Doe", company_name="Acme")
        assert len(results) == 3
        assert mock.text.call_count == 2
        first_call_args = mock.text.call_args_list[0][1]
        assert (
            "Acme" in first_call_args["keywords"] or "Jane Doe Acme" in first_call_args["keywords"]
        )
        assert mock.text.call_args_list[0][1]["max_results"] == 7

    def test_empty_company_skips_retry(self, mock_ddgs: MagicMock) -> None:
        service = GuestSearchService(ddgs=mock_ddgs)
        results = service.search("Jane Doe")
        assert len(results) == 2
        mock_ddgs.text.assert_called_once()

    def test_custom_exception_hierarchy(self) -> None:
        assert issubclass(SearchError, Exception)

    def test_search_raises_search_error_on_failure(self) -> None:
        mock = MagicMock()
        mock.text.side_effect = Exception("Connection failed")
        service = GuestSearchService(ddgs=mock)
        with pytest.raises(SearchError):
            service.search("Jane Doe")

    def test_rate_limiting_respected(self) -> None:
        import time

        mock = MagicMock()
        mock.text.return_value = [{"title": "T", "href": "https://ex.com", "body": "B"}]
        service = GuestSearchService(ddgs=mock)
        t0 = time.time()
        service.search("Test")
        service.search("Test")
        elapsed = time.time() - t0
        assert elapsed >= 5.0
