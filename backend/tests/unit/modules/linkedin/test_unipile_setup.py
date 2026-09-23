from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.autopilot import AutopilotSettingsModel
from src.gateways.unipile_gateway import UnipileGateway
from src.modules.linkedin.models import AutoPilotConfig
from src.modules.linkedin.worker import scheduler as scheduler_module


def test_requested_daily_caps_are_canonical_defaults() -> None:
    api_settings = AutopilotSettingsModel()
    worker_settings = AutoPilotConfig()

    assert api_settings.daily_connections == 10
    assert api_settings.daily_likes == 15
    assert api_settings.daily_comments == 5
    assert api_settings.master_active is False
    assert worker_settings.daily_invite_limit == 25
    assert worker_settings.daily_like_limit == 40
    assert worker_settings.daily_comment_limit == 15


def test_unipile_configuration_detection() -> None:
    assert UnipileGateway(dsn="https://api1.unipile.com:13XXX", token="").is_configured is False
    assert (
        UnipileGateway(dsn="https://api.example.invalid:1234", token="test-token").is_configured
        is True
    )


@pytest.mark.asyncio
async def test_like_uses_official_reaction_endpoint() -> None:
    response = AsyncMock()
    response.status_code = 201
    response.text = "{}"
    client = AsyncMock()
    client.post.return_value = response
    context = AsyncMock()
    context.__aenter__.return_value = client

    with patch("src.gateways.unipile_gateway.httpx.AsyncClient", return_value=context):
        success = await UnipileGateway(
            dsn="https://api.example.invalid:1234", token="test-token"
        ).like_post("account-1", "urn:li:activity:123")

    assert success is True
    client.post.assert_awaited_once()
    url = client.post.await_args.args[0]
    payload = client.post.await_args.kwargs["json"]
    assert url.endswith("/api/v1/posts/reaction")
    assert payload == {
        "account_id": "account-1",
        "post_id": "urn:li:activity:123",
        "reaction_type": "like",
    }


@pytest.mark.asyncio
async def test_hosted_auth_link_is_linkedin_only_and_never_leaks_key() -> None:
    response = MagicMock()
    response.status_code = 200
    response.text = '{"object":"HostedAuthURL","url":"https://account.unipile.com/x"}'
    response.json.return_value = {
        "object": "HostedAuthURL",
        "url": "https://account.unipile.com/x",
    }
    client = AsyncMock()
    client.post.return_value = response
    context = AsyncMock()
    context.__aenter__.return_value = client

    with patch("src.gateways.unipile_gateway.httpx.AsyncClient", return_value=context):
        url = await UnipileGateway(
            dsn="https://api.example.invalid:1234", token="test-token"
        ).create_hosted_auth_link(
            name="user-123",
            success_redirect_url="https://app/success",
            failure_redirect_url="https://app/failure",
            notify_url="https://api/notify",
            expires_on="2026-01-01T00:00:00.000Z",
        )

    assert url == "https://account.unipile.com/x"
    endpoint = client.post.await_args.args[0]
    assert endpoint.endswith("/api/v1/hosted/accounts/link")
    payload = client.post.await_args.kwargs["json"]
    assert payload["type"] == "create"
    assert payload["providers"] == ["LINKEDIN"]  # LinkedIn only, never "*"
    assert payload["name"] == "user-123"
    headers = client.post.await_args.kwargs["headers"]
    # The API key travels only in the server-side header, never in the payload.
    assert headers["X-API-KEY"] == "test-token"
    assert "test-token" not in str(payload)


@pytest.mark.asyncio
async def test_connection_request_omits_empty_message() -> None:
    response = MagicMock()
    response.status_code = 200
    response.text = '{"id":"invite-1"}'
    response.json.return_value = {"id": "invite-1"}
    client = AsyncMock()
    client.post.return_value = response
    context = AsyncMock()
    context.__aenter__.return_value = client

    with patch("src.gateways.unipile_gateway.httpx.AsyncClient", return_value=context):
        invitation_id = await UnipileGateway(
            dsn="https://api.example.invalid:1234", token="test-token"
        ).send_connection_request("account-1", "profile-1", "")

    assert invitation_id == "invite-1"
    assert client.post.await_args.kwargs["json"] == {
        "account_id": "account-1",
        "provider_id": "profile-1",
    }


def test_scheduler_registers_core_jobs(monkeypatch) -> None:
    class FakeScheduler:
        running = False

        def __init__(self) -> None:
            self.jobs: list[tuple[object, str, dict]] = []

        def add_job(self, function, trigger, **kwargs) -> None:
            self.jobs.append((function, trigger, kwargs))

        def start(self) -> None:
            self.running = True

    fake = FakeScheduler()
    monkeypatch.setattr(scheduler_module, "get_scheduler", lambda: fake)

    scheduler_module.start_linkedin_scheduler()

    job_ids = {job[2].get("id") for job in fake.jobs}
    assert "linkedin_post_publisher" in job_ids
    assert "linkedin_post_publisher_startup" in job_ids
    assert "linkedin_engagement_planner" in job_ids
    assert any(job[0] is scheduler_module._plan_and_schedule_day for job in fake.jobs)


@pytest.mark.asyncio
async def test_search_people_uses_post_and_canonical_contract() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"items": [{"id": "prof_1", "name": "Alice"}]}
    client = AsyncMock()
    client.post.return_value = response
    context = AsyncMock()
    context.__aenter__.return_value = client

    with patch("src.gateways.unipile_gateway.httpx.AsyncClient", return_value=context):
        results = await UnipileGateway(
            dsn="https://api.example.invalid:1234", token="test-token"
        ).search_people(account_id="acc-123", keywords="founder", limit=10)

    assert len(results) == 1
    assert results[0]["id"] == "prof_1"
    client.post.assert_awaited_once()
    url = client.post.await_args.args[0]
    params = client.post.await_args.kwargs.get("params")
    payload = client.post.await_args.kwargs.get("json")
    assert url.endswith("/api/v1/linkedin/search")
    assert params == {"account_id": "acc-123"}
    assert payload == {
        "api": "classic",
        "category": "people",
        "keywords": "founder",
    }


@pytest.mark.asyncio
async def test_get_user_posts_uses_canonical_user_endpoint() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"items": [{"id": "post_1", "text": "Hello world"}]}
    client = AsyncMock()
    client.get.return_value = response
    context = AsyncMock()
    context.__aenter__.return_value = client

    with patch("src.gateways.unipile_gateway.httpx.AsyncClient", return_value=context):
        posts = await UnipileGateway(
            dsn="https://api.example.invalid:1234", token="test-token"
        ).get_user_posts(account_id="acc-123", profile_id="prof_456", limit=5)

    assert len(posts) == 1
    assert posts[0]["id"] == "post_1"
    client.get.assert_awaited_once()
    url = client.get.await_args.args[0]
    params = client.get.await_args.kwargs.get("params")
    assert url.endswith("/api/v1/users/prof_456/posts")
    assert params == {"account_id": "acc-123", "limit": "5"}
