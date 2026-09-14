import pytest

from src.gateways.mock_unipile_gateway import MockUnipileGateway


@pytest.mark.asyncio
async def test_mock_gateway_returns_dummy_data():
    gateway = MockUnipileGateway()

    # Test list_accounts
    accounts = await gateway.list_accounts()
    assert len(accounts) == 1
    assert accounts[0]["id"] == "mock_account_001"

    # Test search_people
    profiles = await gateway.search_people("mock_account_001", "AI Founder")
    assert isinstance(profiles, list)
    assert len(profiles) > 0
    assert "mock_profile_0" in profiles[0]["provider_id"]

    # Test get_user_posts
    posts = await gateway.get_user_posts("mock_account_001", "mock_profile_001")
    assert isinstance(posts, list)
    assert len(posts) == 5
    assert "text" in posts[0]

    # Test mutations return IDs
    post_id = await gateway.create_post("mock_account", "hello")
    assert "mock_post_" in post_id

    like_res = await gateway.like_post("mock_account", "post_123")
    assert like_res is True

    comment_id = await gateway.comment_on_post("mock_account", "post_123", "Nice")
    assert "mock_comment" in comment_id
