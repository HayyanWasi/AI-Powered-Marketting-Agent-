from unittest.mock import MagicMock

import pytest

from src.models.guest_profile import ConfidenceLevel
from src.services.llm import LLMService, LLMError


class TestLLMService:
    def test_analyze_returns_guest_profile(self, mock_llm: MagicMock) -> None:
        service = LLMService(client=mock_llm)
        results = [
            {
                "title": "Jane Doe - Researcher",
                "href": "https://ex.com",
                "body": "Jane Doe is a researcher.",
            },
        ]
        profile = service.analyze_search_results(results)
        assert profile.full_name == "Jane Doe"
        assert profile.current_position == "AI Researcher"
        assert profile.organization == "TechCorp"
        assert profile.confidence_level == ConfidenceLevel.HIGH
        assert len(profile.sources_used) == 1

    def test_empty_results(self, mock_llm: MagicMock) -> None:
        service = LLMService(client=mock_llm)
        profile = service.analyze_search_results([])
        assert profile.full_name == "Jane Doe"
        assert profile.confidence_level == ConfidenceLevel.HIGH

    def test_partial_results(self, mock_llm: MagicMock) -> None:
        parse_result = MagicMock()
        parse_result.choices = [
            MagicMock(
                message=MagicMock(
                    parsed=MagicMock(
                        full_name="John",
                        current_position="",
                        organization="",
                        professional_biography="",
                        areas_of_expertise=[],
                        confidence_level=ConfidenceLevel.LOW,
                        sources_used=[],
                    ),
                    refusal=None,
                ),
            ),
        ]
        parse_result.choices[0].message.parsed.full_name = "John"
        parse_result.choices[0].message.parsed.current_position = ""
        parse_result.choices[0].message.parsed.organization = ""
        parse_result.choices[0].message.parsed.professional_biography = ""
        parse_result.choices[0].message.parsed.areas_of_expertise = []
        parse_result.choices[0].message.parsed.confidence_level = ConfidenceLevel.LOW
        parse_result.choices[0].message.parsed.sources_used = []

        client_instance = MagicMock()
        completion = MagicMock()
        completion.parse.return_value = parse_result
        client_instance.chat.completions = completion

        service = LLMService(client=client_instance)
        profile = service.analyze_search_results(
            [{"title": "T", "href": "https://ex.com", "body": "B"}]
        )
        assert profile.full_name == "John"
        assert profile.current_position == ""
        assert profile.confidence_level == ConfidenceLevel.LOW

    def test_llm_error_raises_llm_error(self, mock_llm: MagicMock) -> None:
        mock_llm.chat.completions.parse.side_effect = Exception("OpenAI API error")
        service = LLMService(client=mock_llm)
        with pytest.raises(LLMError):
            service.analyze_search_results([{"title": "T", "href": "https://ex.com", "body": "B"}])

    def test_custom_exception_hierarchy(self) -> None:
        assert issubclass(LLMError, Exception)
