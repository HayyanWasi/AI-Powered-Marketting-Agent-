from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.linkedin.models import ResolvedTarget, TargetPersona
from src.modules.linkedin.worker.target_resolver import TargetResolver


@pytest.fixture
def mock_supabase():
    with patch("src.modules.linkedin.worker.target_resolver.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_gateway():
    with patch("src.modules.linkedin.worker.target_resolver.get_unipile_gateway") as mock:
        mock_gw = MagicMock()
        mock.return_value = mock_gw
        yield mock_gw


@pytest.mark.asyncio
async def test_load_personas(mock_supabase):
    mock_execute = MagicMock()
    mock_execute.execute.return_value = MagicMock(
        data=[
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "company_profile_id": "22222222-2222-2222-2222-222222222222",
                "label": "Test Persona",
                "search_keywords": "AI Founder",
                "max_profiles": 20,
                "created_at": datetime.now(UTC).isoformat(),
            }
        ]
    )
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value = (
        mock_execute
    )

    resolver = TargetResolver()
    personas = await resolver.load_personas("22222222-2222-2222-2222-222222222222")

    assert len(personas) == 1
    assert personas[0].label == "Test Persona"
    assert personas[0].search_keywords == "AI Founder"
    assert str(personas[0].company_profile_id) == "22222222-2222-2222-2222-222222222222"
    assert not hasattr(personas[0], "account_id")


@pytest.mark.asyncio
async def test_get_engagement_targets_deduplication(mock_supabase, mock_gateway):
    # Mock personas
    personas = [
        TargetPersona(account_id="test_account", label="Test Persona", search_keywords="AI Founder")
    ]

    resolver = TargetResolver()

    # We patch resolve_personas directly to avoid conflicting with the dedup mock chain
    from src.modules.linkedin.models import ResolvedTarget

    mock_rt = ResolvedTarget(account_id="test", persona_label="Test", profile_id="prof_1")

    with patch.object(resolver, "resolve_personas", return_value=[mock_rt]):
        # Mock the gateway to return two posts
        from unittest.mock import AsyncMock

        mock_gateway.get_user_posts = AsyncMock(
            return_value=[
                {
                    "id": "post_1",
                    "text": "Post 1 text that is definitely longer than fifty characters to pass the length filter",
                    "author": {"name": "Author 1"},
                    "created_at": datetime.now(UTC).isoformat(),
                },
                {
                    "id": "post_2",
                    "text": "Post 2 text that is also longer than fifty characters so it does not get skipped",
                    "author": {"name": "Author 1"},
                    "created_at": datetime.now(UTC).isoformat(),
                },
            ]
        )

        # Mock Supabase engaged_posts query to simulate that 'post_1' was already engaged
        mock_dedup = MagicMock()
        mock_dedup.execute.return_value = MagicMock(data=[{"post_id": "post_1"}])
        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_dedup

        # Run the get_engagement_targets
        targets = await resolver.get_engagement_targets("test_account", personas, count=5)

        # Since post_1 was in the DB, it should have been filtered out. Only post_2 should remain.
        assert len(targets) == 1
        assert targets[0].post_id == "post_2"


@pytest.mark.asyncio
async def test_record_engagement(mock_supabase):
    mock_supabase.table().upsert.return_value = MagicMock()

    resolver = TargetResolver()
    await resolver.record_engagement("test_account", "post_1", "like")

    # Check that either insert or upsert was called
    mock_supabase.table().upsert.assert_called_once()
    args = mock_supabase.table().upsert.call_args[0][0]
    assert args["post_id"] == "post_1"
    assert args["action_type"] == "like"


@pytest.mark.asyncio
async def test_resolve_personas_uses_unipile_account_id_for_gateway(mock_supabase, mock_gateway):
    mock_supabase.table().select().eq().eq().order().limit().execute.return_value = MagicMock(
        data=[]
    )
    mock_supabase.table().upsert().execute.return_value = MagicMock()

    mock_gateway.search_people = AsyncMock(
        return_value=[
            {
                "id": "prof_unipile_1",
                "provider_id": "prof_unipile_1",
                "name": "Jane Doe",
                "headline": "Engineer",
            }
        ]
    )

    persona = TargetPersona(
        company_profile_id="22222222-2222-2222-2222-222222222222",
        label="Tech Leads",
        search_keywords="tech lead",
        max_profiles=10,
    )
    resolver = TargetResolver()

    # Call with internal UUID and provider unipile ID
    results = await resolver.resolve_personas(
        account_id="internal-uuid-123",
        personas=[persona],
        unipile_account_id="unipile-acc-789",
    )

    assert len(results) == 1
    assert results[0].account_id == "internal-uuid-123"
    assert results[0].profile_id == "prof_unipile_1"

    # Gateway MUST receive unipile_account_id
    mock_gateway.search_people.assert_awaited_once_with("unipile-acc-789", "tech lead", 10)

    # Database upsert MUST use internal account_id
    upsert_data = None
    for c in mock_supabase.table().upsert.call_args_list:
        if c.args:
            upsert_data = c.args[0]
            break
    assert upsert_data is not None
    assert upsert_data["account_id"] == "internal-uuid-123"


@pytest.mark.asyncio
async def test_fetch_target_posts_uses_unipile_account_id_for_gateway(mock_gateway):
    mock_gateway.get_user_posts = AsyncMock(
        return_value=[
            {
                "id": "post_ext_1",
                "text": "This is a meaningful post with enough length to be processed by target post resolution.",
                "created_at": datetime.now(UTC).isoformat(),
            }
        ]
    )

    resolver = TargetResolver()
    rt = ResolvedTarget(
        account_id="internal-uuid-123",
        persona_label="Tech Leads",
        profile_id="prof_external_1",
        display_name="Jane Doe",
    )

    posts = await resolver.fetch_target_posts(
        account_id="internal-uuid-123",
        resolved_targets=[rt],
        unipile_account_id="unipile-acc-789",
    )

    assert len(posts) == 1
    assert posts[0].post_id == "post_ext_1"

    # Gateway get_user_posts MUST be called with unipile_account_id
    mock_gateway.get_user_posts.assert_awaited_once_with("unipile-acc-789", "prof_external_1", 3)
