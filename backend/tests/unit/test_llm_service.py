"""Unit tests for LLMService — uses OpenRouter / json_object parsing."""

import json
from unittest.mock import MagicMock

import pytest

from src.models.guest_profile import ConfidenceLevel
from src.services.llm import LLMError, LLMService


def _make_client(response_text: str) -> MagicMock:
    """Build a mock OpenAI client whose .chat.completions.create() returns response_text."""
    msg = MagicMock()
    msg.content = response_text
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    client = MagicMock()
    client.chat.completions.create.return_value = completion
    return client


_FULL_RESPONSE = json.dumps(
    {
        "full_name": "Jane Doe",
        "current_position": "AI Researcher",
        "organization": "TechCorp",
        "professional_biography": "Jane Doe is a leading AI researcher.",
        "areas_of_expertise": ["NLP", "Machine Learning"],
        "confidence_level": "HIGH",
    }
)

_RESULTS = [
    {
        "title": "Jane Doe - Researcher",
        "href": "https://ex.com",
        "body": "Jane Doe is a researcher.",
    }
]


class TestLLMService:
    def test_analyze_returns_guest_profile(self) -> None:
        client = _make_client(_FULL_RESPONSE)
        service = LLMService(client=client)
        profile = service.analyze_search_results(_RESULTS)
        assert profile.full_name == "Jane Doe"
        assert profile.current_position == "AI Researcher"
        assert profile.organization == "TechCorp"
        assert profile.confidence_level == ConfidenceLevel.HIGH

    def test_empty_results(self) -> None:
        client = _make_client(_FULL_RESPONSE)
        service = LLMService(client=client)
        profile = service.analyze_search_results([])
        assert profile.full_name == "Jane Doe"
        assert profile.confidence_level == ConfidenceLevel.HIGH

    def test_partial_results(self) -> None:
        partial = json.dumps(
            {
                "full_name": "John",
                "current_position": "",
                "organization": "",
                "professional_biography": "",
                "areas_of_expertise": [],
                "confidence_level": "LOW",
            }
        )
        client = _make_client(partial)
        service = LLMService(client=client)
        profile = service.analyze_search_results(_RESULTS)
        assert profile.full_name == "John"
        assert profile.current_position == ""
        assert profile.confidence_level == ConfidenceLevel.LOW

    def test_json_fenced_response_is_parsed(self) -> None:
        """LLM wraps JSON in markdown code fence — should still parse."""
        fenced = f"```json\n{_FULL_RESPONSE}\n```"
        client = _make_client(fenced)
        service = LLMService(client=client)
        profile = service.analyze_search_results(_RESULTS)
        assert profile.full_name == "Jane Doe"

    def test_unknown_confidence_falls_back_to_low(self) -> None:
        data = json.loads(_FULL_RESPONSE)
        data["confidence_level"] = "UNKNOWN"
        client = _make_client(json.dumps(data))
        service = LLMService(client=client)
        profile = service.analyze_search_results(_RESULTS)
        assert profile.confidence_level == ConfidenceLevel.LOW

    def test_llm_error_raises_llm_error(self) -> None:
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("API error")
        service = LLMService(client=client)
        with pytest.raises(LLMError):
            service.analyze_search_results(_RESULTS)

    def test_invalid_json_raises_llm_error(self) -> None:
        client = _make_client("not json at all")
        service = LLMService(client=client)
        with pytest.raises(LLMError):
            service.analyze_search_results(_RESULTS)

    def test_custom_exception_hierarchy(self) -> None:
        assert issubclass(LLMError, Exception)
