"""Pytest configuration and fixtures."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.campaign import Campaign, CampaignState, Goals, Schedule, TargetAudience
from src.models.guest_profile import ConfidenceLevel
from src.models.history import CampaignHistoryEntry, EventType


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_llm() -> MagicMock:
    """Mock OpenAI LLM client for testing."""
    parse_result = MagicMock()
    parse_result.choices = [
        MagicMock(
            message=MagicMock(
                parsed=MagicMock(
                    full_name="Jane Doe",
                    current_position="AI Researcher",
                    organization="TechCorp",
                    professional_biography="Jane Doe is a leading AI researcher.",
                    areas_of_expertise=["AI", "NLP"],
                    confidence_level=ConfidenceLevel.HIGH,
                    sources_used=[
                        MagicMock(
                            website_name="example.com",
                            page_title="Jane Doe - Researcher",
                            snippet="Jane Doe is a researcher.",
                            source_url="https://ex.com",
                        )
                    ],
                ),
                refusal=None,
            ),
        ),
    ]
    client_instance = MagicMock()
    completion = MagicMock()
    completion.parse.return_value = parse_result
    client_instance.chat.completions = completion
    return client_instance


@pytest.fixture
def mock_ddgs() -> MagicMock:
    """Mock DuckDuckGo search client for testing."""
    mock = MagicMock()
    mock.text.return_value = [
        {
            "title": "Jane Doe - AI Researcher at TechCorp",
            "href": "https://example.com/jane-doe",
            "body": "Jane Doe is a leading AI researcher specializing in natural language processing.",
        },
        {
            "title": "Jane Doe - Speaker at AI Summit",
            "href": "https://example.com/jane-doe-ai-summit",
            "body": "Jane Doe spoke about AI safety at the annual AI Summit.",
        },
    ]
    return mock


@pytest.fixture
def mock_ddgs_no_results() -> MagicMock:
    """Mock DuckDuckGo search client returning no results."""
    mock = MagicMock()
    mock.text.return_value = []
    return mock


@pytest.fixture
def sample_campaign():
    """Create a sample campaign for testing."""
    return Campaign(
        id=uuid4(),
        organization_id=uuid4(),
        name="Test Campaign",
        goals=Goals(primary="Increase sales", metrics=["revenue"], targets={"revenue": 10000}),
        target_audience=TargetAudience(
            segments=["customers"], demographics={}, interests=["shopping"]
        ),
        platforms=["instagram", "facebook"],
        schedule=Schedule(
            start_date=datetime(2026, 11, 1),
            end_date=datetime(2026, 12, 31),
            timezone="America/New_York",
        ),
        metadata={"budget": 5000},
        state=CampaignState.DRAFT,
        version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by=uuid4(),
        updated_by=uuid4(),
    )


@pytest.fixture
def sample_history_entry():
    """Create a sample history entry for testing."""
    return CampaignHistoryEntry(
        id=uuid4(),
        campaign_id=uuid4(),
        event_type=EventType.CREATED,
        timestamp=datetime.utcnow(),
        actor_id=uuid4(),
        from_state=None,
        to_state=CampaignState.DRAFT,
        snapshot={"name": "Test Campaign"},
    )


# Test markers
pytestmark = [
    pytest.mark.asyncio,
]
