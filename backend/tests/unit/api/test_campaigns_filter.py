"""Unit tests for campaign list brand filtering and tenant boundary."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.main import app
from src.models.campaign import Campaign, CampaignState
from src.repositories.campaign_repository import CampaignRepository
from src.services.campaign_service import CampaignService


@pytest.fixture
def mock_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        id=str(uuid4()),
        email="test@example.com",
        roles=["authenticated"],
    )


@pytest.fixture
def client(mock_user: AuthenticatedUser) -> TestClient:
    app.dependency_overrides[get_authenticated_user] = lambda: mock_user
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_campaign(org_id: str, brand_id: str) -> Campaign:
    return Campaign(
        id=uuid4(),
        organization_id=UUID(org_id),
        company_profile_id=UUID(brand_id),
        name="Test Campaign",
        state=CampaignState.DRAFT,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_list_campaigns_passes_brand_filter_to_service(mock_user: AuthenticatedUser) -> None:
    brand_id = uuid4()
    mock_svc = MagicMock(spec=CampaignService)
    mock_svc.list_campaigns = AsyncMock(
        return_value=([_make_campaign(mock_user.id, str(brand_id))], 1)
    )

    from src.api.v1.campaigns import list_campaigns

    res = await list_campaigns(
        company_profile_id=brand_id,
        state=None,
        page=1,
        page_size=20,
        owner_id=None,
        svc=mock_svc,
        user=mock_user,
    )

    call_kwargs = mock_svc.list_campaigns.call_args.kwargs
    assert call_kwargs["organization_id"] == UUID(mock_user.id)
    assert call_kwargs["company_profile_id"] == brand_id
    assert call_kwargs["page"] == 1
    assert call_kwargs["page_size"] == 20
    assert res.total == 1
    assert len(res.campaigns) == 1
    assert res.campaigns[0].company_profile_id == brand_id


@pytest.mark.asyncio
async def test_campaign_repository_list_applies_both_filters() -> None:
    org_id = uuid4()
    brand_id = uuid4()

    repo = CampaignRepository()
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_query = MagicMock()

    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[], count=0)

    repo._client = mock_client

    campaigns, total = await repo.list(
        organization_id=org_id,
        company_profile_id=brand_id,
        page=2,
        page_size=10,
    )

    # Verify table and select
    mock_client.table.assert_called_with("campaigns")
    mock_table.select.assert_called_with("*", count="exact")

    # Verify eq filters applied for both organization_id and company_profile_id
    eq_calls = [call.args for call in mock_query.eq.call_args_list]
    assert ("organization_id", str(org_id)) in eq_calls
    assert ("company_profile_id", str(brand_id)) in eq_calls

    # Verify pagination range (page 2, size 10 => 10 to 19)
    mock_query.range.assert_called_with(10, 19)
    assert campaigns == []
    assert total == 0
