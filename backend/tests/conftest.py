from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from src.models.guest_profile import ConfidenceLevel, GuestProfileData, SearchResultData


@pytest.fixture
def mock_ddgs() -> Generator[MagicMock, None, None]:
    with patch("src.services.search.DDGS") as mock:
        instance = mock.return_value
        instance.text.return_value = [
            {
                "title": "Jane Doe - AI Researcher at TechCorp",
                "href": "https://example.com/jane-doe",
                "body": "Jane Doe is a leading AI researcher specializing in natural language processing.",
            },
            {
                "title": "Dr. Jane Doe Profile",
                "href": "https://example.com/dr-jane",
                "body": "Dr. Jane Doe, PhD in Computer Science, currently leading ML research at TechCorp.",
            },
        ]
        yield instance


@pytest.fixture
def mock_ddgs_no_results() -> Generator[MagicMock, None, None]:
    with patch("src.services.search.DDGS") as mock:
        instance = mock.return_value
        instance.text.return_value = []
        yield instance


@pytest.fixture
def mock_ddgs_single_result() -> Generator[MagicMock, None, None]:
    with patch("src.services.search.DDGS") as mock:
        instance = mock.return_value
        instance.text.side_effect = [
            [
                {
                    "title": "Only Result",
                    "href": "https://example.com",
                    "body": "Single result body.",
                }
            ],
        ]
        yield instance


@pytest.fixture
def mock_llm() -> Generator[MagicMock, None, None]:
    with patch("src.services.llm.OpenAI") as mock:
        client_instance = mock.return_value
        parse_result = MagicMock()
        parse_result.choices = [
            MagicMock(
                message=MagicMock(
                    parsed=GuestProfileData(
                        full_name="Jane Doe",
                        current_position="AI Researcher",
                        organization="TechCorp",
                        professional_biography="Jane Doe is a leading AI researcher at TechCorp.",
                        areas_of_expertise=["Natural Language Processing", "Machine Learning"],
                        confidence_level=ConfidenceLevel.HIGH,
                        sources_used=[
                            SearchResultData(
                                website_name="example.com",
                                page_title="Jane Doe - AI Researcher at TechCorp",
                                snippet="Jane Doe is a leading AI researcher...",
                                source_url="https://example.com/jane-doe",
                            ),
                        ],
                    ),
                    refusal=None,
                ),
            ),
        ]
        parse_result.choices[0].message.parsed = GuestProfileData(
            full_name="Jane Doe",
            current_position="AI Researcher",
            organization="TechCorp",
            professional_biography="Jane Doe is a leading AI researcher at TechCorp.",
            areas_of_expertise=["Natural Language Processing", "Machine Learning"],
            confidence_level=ConfidenceLevel.HIGH,
            sources_used=[
                SearchResultData(
                    website_name="example.com",
                    page_title="Jane Doe - AI Researcher at TechCorp",
                    snippet="Jane Doe is a leading AI researcher...",
                    source_url="https://example.com/jane-doe",
                ),
            ],
        )
        completion = MagicMock()
        completion.parse.return_value = parse_result
        client_instance.chat.completions = completion
        yield client_instance
