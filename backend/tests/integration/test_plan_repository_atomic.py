from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.modules.planning.models.campaign_plan import CampaignPlan, PlanStatus
from src.modules.planning.repositories.plan_repository import PlanRepository


@pytest.fixture
def mock_supabase_client():
    return MagicMock()


@pytest.fixture
def repo(mock_supabase_client, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:8000")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    repo = PlanRepository()
    repo._client = mock_supabase_client
    return repo


@pytest.mark.asyncio
async def test_add_version_normal_creation(repo, mock_supabase_client):
    plan_id = uuid4()
    plan = CampaignPlan(
        version=1,
        status=PlanStatus.DRAFT,
        language="en",
        input_identity=None,
        sections=(),
    )

    # Mock successful RPC call
    mock_rpc = MagicMock()
    mock_execute = MagicMock()

    mock_execute.return_value.data = {
        "id": str(uuid4()),
        "plan_id": str(plan_id),
        "version": 1,
        "document": {},
        "created_at": "2026-09-16T12:00:00Z",
    }
    mock_rpc.return_value.execute = mock_execute
    mock_supabase_client.rpc = mock_rpc

    version = await repo.add_version(plan_id, plan)

    mock_supabase_client.rpc.assert_called_once_with(
        "add_plan_version",
        {
            "p_plan_id": str(plan_id),
            "p_version": 1,
            "p_document": plan.to_document(),
            "p_parent_version": None,
            "p_change_summary": "",
            "p_sections_changed": [],
            "p_status": "Draft",
            "p_language": "en",
        },
    )

    assert version.version == 1
    assert version.plan_id == plan_id


@pytest.mark.asyncio
async def test_add_version_forces_failure_during_update(repo, mock_supabase_client):
    plan_id = uuid4()
    plan = CampaignPlan(
        version=1,
        status=PlanStatus.DRAFT,
        language="en",
        input_identity=None,
        sections=(),
    )

    # Mock failed RPC call
    mock_rpc = MagicMock()
    mock_execute = MagicMock()

    # RPC fails/returns no data (e.g. exception from Postgres)
    mock_execute.return_value.data = None
    mock_rpc.return_value.execute = mock_execute
    mock_supabase_client.rpc = mock_rpc

    with pytest.raises(RuntimeError, match=f"Failed to store version 1 for plan {plan_id}"):
        await repo.add_version(plan_id, plan)

    # Asserts that if it fails, it raised RuntimeError immediately
    # Because it is one RPC, pointer and version insert fail together
    mock_supabase_client.rpc.assert_called_once()
