"""Focused authorization tests for campaign-scoped LinkedIn API routes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.config.settings import settings
from src.main import app
from src.models.errors import NotFoundError

USER_A = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
USER_B = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
CAMPAIGN_A = uuid4()
CAMPAIGN_B = uuid4()
POST_A = uuid4()
PRIVATE_SENTINEL = "USER_A_PRIVATE_SENTINEL"


class _Query:
    def __init__(self, data: list[dict]) -> None:
        self.data = data
        self.filters: dict[str, str] = {}

    def select(self, *_args, **_kwargs):
        return self

    def update(self, *_args, **_kwargs):
        return self

    def eq(self, field: str, value: str):
        self.filters[field] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        rows = [
            row
            for row in self.data
            if all(str(row.get(field)) == value for field, value in self.filters.items())
        ]
        return SimpleNamespace(data=rows)


class _Repository:
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name
        self.rows = (
            [
                {
                    "id": str(POST_A),
                    "campaign_id": str(CAMPAIGN_A),
                    "body": PRIVATE_SENTINEL,
                    "full_content": PRIVATE_SENTINEL,
                    "status": "draft",
                }
            ]
            if table_name == "linkedin_posts"
            else []
        )
        self.client = self

    def table(self, _table_name: str) -> _Query:
        return _Query(self.rows)


@pytest.fixture(autouse=True)
def _clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _as(user: AuthenticatedUser) -> None:
    app.dependency_overrides[get_authenticated_user] = lambda: user


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("get", f"/api/v1/linkedin/campaigns/{CAMPAIGN_A}/preview", None),
        ("get", f"/api/v1/linkedin/campaigns/{CAMPAIGN_A}/status", None),
        ("patch", f"/api/v1/linkedin/campaigns/{CAMPAIGN_A}/posts/{POST_A}", {"body": "x"}),
        ("post", f"/api/v1/linkedin/campaigns/{CAMPAIGN_A}/launch", {"account_id": "a"}),
    ],
)
def test_anonymous_linkedin_private_routes_are_denied_before_repository_access(
    monkeypatch, method: str, path: str, json_body: dict | None
) -> None:
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)
    repository = patch("src.api.v1.linkedin.BaseRepository")
    with repository as repo_cls:
        response = TestClient(app).request(method, path, json=json_body)

    assert response.status_code == 401
    assert PRIVATE_SENTINEL not in response.text
    repo_cls.assert_not_called()


def test_owner_preview_is_allowed_and_returns_owned_content() -> None:
    _as(USER_A)
    owner_check = AsyncMock(return_value=None)
    with (
        patch("src.api.v1.linkedin._require_campaign_owner", new=owner_check),
        patch("src.api.v1.linkedin.BaseRepository", side_effect=_Repository),
    ):
        response = TestClient(app).get(
            f"/api/v1/linkedin/campaigns/{CAMPAIGN_A}/preview"
        )

    assert response.status_code == 200
    assert PRIVATE_SENTINEL in response.text
    owner_check.assert_awaited_once_with(CAMPAIGN_A, USER_A)


def test_foreign_preview_is_denied_before_repository_access() -> None:
    _as(USER_B)
    repository = patch("src.api.v1.linkedin.BaseRepository")
    with (
        patch(
            "src.api.v1.linkedin._require_campaign_owner",
            new=AsyncMock(side_effect=NotFoundError("Campaign", str(CAMPAIGN_A))),
        ),
        repository as repo_cls,
    ):
        response = TestClient(app).get(
            f"/api/v1/linkedin/campaigns/{CAMPAIGN_A}/preview"
        )

    assert response.status_code == 404
    assert PRIVATE_SENTINEL not in response.text
    repo_cls.assert_not_called()


@pytest.mark.asyncio
async def test_campaign_owner_guard_uses_authenticated_user_id() -> None:
    from src.api.v1.linkedin import _require_campaign_owner

    get_campaign = AsyncMock(return_value=SimpleNamespace(id=CAMPAIGN_A))
    service = SimpleNamespace(get_campaign=get_campaign)
    with patch("src.api.v1.linkedin.CampaignService", return_value=service):
        await _require_campaign_owner(CAMPAIGN_A, USER_A)

    get_campaign.assert_awaited_once_with(CAMPAIGN_A, UUID(USER_A.id))


def test_anonymous_generation_is_denied_before_context_or_llm(monkeypatch) -> None:
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)
    resolve = AsyncMock()
    generate = AsyncMock()
    with (
        patch("src.api.v1.linkedin.CampaignContextResolver.resolve", new=resolve),
        patch(
            "src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts",
            new=generate,
        ),
    ):
        response = TestClient(app).post(
            f"/api/v1/linkedin/campaigns/{CAMPAIGN_A}/generate", json={}
        )

    assert response.status_code == 401
    resolve.assert_not_awaited()
    generate.assert_not_awaited()


def test_foreign_generation_is_denied_before_llm_or_persistence() -> None:
    _as(USER_B)
    resolve = AsyncMock(side_effect=HTTPException(404, "Campaign not found or access denied."))
    generate = AsyncMock()
    repository = patch("src.api.v1.linkedin.BaseRepository")
    with (
        patch("src.api.v1.linkedin.CampaignContextResolver.resolve", new=resolve),
        patch(
            "src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts",
            new=generate,
        ),
        repository as repo_cls,
    ):
        response = TestClient(app).post(
            f"/api/v1/linkedin/campaigns/{CAMPAIGN_A}/generate", json={}
        )

    assert response.status_code == 404
    assert PRIVATE_SENTINEL not in response.text
    generate.assert_not_awaited()
    repo_cls.assert_not_called()


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("patch", f"/api/v1/linkedin/campaigns/{CAMPAIGN_A}/posts/{POST_A}", {"body": "foreign"}),
        ("post", f"/api/v1/linkedin/campaigns/{CAMPAIGN_A}/launch", {"account_id": "foreign"}),
        ("get", f"/api/v1/linkedin/campaigns/{CAMPAIGN_A}/status", None),
    ],
)
def test_foreign_mutation_and_status_are_denied_before_private_access(
    method: str, path: str, json_body: dict | None
) -> None:
    _as(USER_B)
    repository = patch("src.api.v1.linkedin.BaseRepository")
    with (
        patch(
            "src.api.v1.linkedin._require_campaign_owner",
            new=AsyncMock(side_effect=NotFoundError("Campaign", str(CAMPAIGN_A))),
        ),
        repository as repo_cls,
    ):
        response = TestClient(app).request(method, path, json=json_body)

    assert response.status_code == 404
    assert PRIVATE_SENTINEL not in response.text
    repo_cls.assert_not_called()


def test_owned_campaign_id_cannot_be_used_to_patch_another_campaigns_post() -> None:
    _as(USER_A)
    owner_check = AsyncMock(return_value=None)
    with (
        patch("src.api.v1.linkedin._require_campaign_owner", new=owner_check),
        patch("src.api.v1.linkedin.BaseRepository", side_effect=_Repository),
    ):
        response = TestClient(app).patch(
            f"/api/v1/linkedin/campaigns/{CAMPAIGN_B}/posts/{POST_A}",
            json={"body": "cross-campaign mutation"},
        )

    assert response.status_code == 404
    assert PRIVATE_SENTINEL not in response.text
