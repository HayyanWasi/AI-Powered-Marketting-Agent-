from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.dependencies import AuthenticatedUser
from src.api.v1.linkedin import generate_campaign_content
from src.models.brand_context import BrandContext
from src.modules.linkedin.models import LinkedInPost, OutreachTemplate, PostStatus
from src.modules.planning.models.campaign_plan import (
    CalendarSlot,
    CampaignPlan,
    ChannelPlan,
    InputIdentity,
)
from src.services.campaign_context_service import (
    compute_brand_fingerprint,
    compute_intake_fingerprint,
)


class _RpcRequest:
    def __init__(self, *, data=None, error: Exception | None = None) -> None:
        self._data = data
        self._error = error

    def execute(self):
        if self._error:
            raise self._error
        return SimpleNamespace(data=self._data)


class _Client:
    def __init__(self, *, data=None, error: Exception | None = None) -> None:
        self.data = data
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def rpc(self, name: str, args: dict) -> _RpcRequest:
        self.calls.append((name, args))
        return _RpcRequest(data=self.data, error=self.error)


def _context():
    campaign_id = uuid4()
    user_id = uuid4()
    profile_id = uuid4()
    brand = BrandContext(
        company_profile_id=profile_id,
        company_name="Task 8 Brand",
        brand_tone="Direct, practical",
        negative_guardrails=("Never use buzzwords",),
        profile_updated_at="2026-09-17T10:00:00+00:00",
    )
    inputs = SimpleNamespace(
        brand=brand,
        intake={"updated_at": "2026-09-17T10:05:00+00:00"},
        campaign=SimpleNamespace(name="Task 8", schedule=None, goals=None, platforms=[]),
    )
    plan = CampaignPlan(
        campaign_id=campaign_id,
        input_identity=InputIdentity(
            campaign_id=campaign_id,
            company_profile_id=profile_id,
            brand_version=compute_brand_fingerprint(inputs.brand),
            intake_hash=compute_intake_fingerprint(inputs.intake, inputs.campaign),
        ),
        channel_plan=ChannelPlan(
            calendar_slots=(
                CalendarSlot(
                    slot_id="task8-slot",
                    date="2026-09-20",
                    platform="LinkedIn",
                    theme="Atomic persistence",
                    cta="Verify",
                ),
            )
        ),
    )
    generated_post = LinkedInPost(
        campaign_id=campaign_id,
        slot_id="task8-slot",
        scheduled_at=datetime(2026, 9, 20, 10, tzinfo=UTC),
        hook="TASK8_SENTINEL_HOOK",
        body="TASK8_SENTINEL_BODY",
        cta_text="TASK8_SENTINEL_CTA",
        full_content="TASK8_SENTINEL_FULL_CONTENT",
        status=PostStatus.DRAFT,
    )
    outreach = OutreachTemplate(
        campaign_id=campaign_id,
        step_invite_msg="TASK8_INVITE",
        step_value_msg="TASK8_VALUE",
        step_followup_msg="TASK8_FOLLOWUP",
    )
    user = AuthenticatedUser(id=str(user_id), roles=["user"], permissions=[])
    return campaign_id, user, inputs, plan, generated_post, outreach


@pytest.mark.asyncio
async def test_generation_returns_only_rows_confirmed_by_atomic_rpc() -> None:
    campaign_id, user, inputs, plan, generated_post, outreach = _context()
    database_post_id = uuid4()
    database_sequence_id = uuid4()
    payload = {
        "posts": [
            {
                **generated_post.to_dict(),
                "id": str(database_post_id),
                "campaign_id": str(campaign_id),
            }
        ],
        "sequence": {
            "id": str(database_sequence_id),
            "campaign_id": str(campaign_id),
        },
    }
    client = _Client(data=payload)
    repository = SimpleNamespace(client=client)

    with (
        patch(
            "src.api.v1.linkedin.CampaignContextResolver.resolve",
            new=AsyncMock(return_value=inputs),
        ),
        patch(
            "src.api.v1.linkedin.PlanRefinementService.get_plan",
            new=AsyncMock(return_value=plan),
        ),
        patch(
            "src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts",
            new=AsyncMock(return_value=[generated_post]),
        ),
        patch(
            "src.api.v1.linkedin.OutreachSequenceGenerator.generate_sequence",
            new=AsyncMock(return_value=outreach),
        ),
        patch("src.api.v1.linkedin.BaseRepository", return_value=repository),
    ):
        response = await generate_campaign_content(campaign_id, user=user)

    assert response["status"] == "success"
    assert response["posts"][0]["id"] == str(database_post_id)
    assert client.calls[0][0] == "replace_linkedin_campaign_content"
    rpc_args = client.calls[0][1]
    assert rpc_args["p_campaign_id"] == str(campaign_id)
    assert rpc_args["p_user_id"] == user.id
    assert "id" not in rpc_args["p_posts"][0]
    assert "campaign_id" not in rpc_args["p_posts"][0]
    assert "created_at" not in rpc_args["p_posts"][0]


@pytest.mark.asyncio
async def test_database_failure_cannot_return_fake_success() -> None:
    campaign_id, user, inputs, plan, generated_post, outreach = _context()
    client = _Client(error=RuntimeError("forced database failure"))
    repository = SimpleNamespace(client=client)

    with (
        patch(
            "src.api.v1.linkedin.CampaignContextResolver.resolve",
            new=AsyncMock(return_value=inputs),
        ),
        patch(
            "src.api.v1.linkedin.PlanRefinementService.get_plan",
            new=AsyncMock(return_value=plan),
        ),
        patch(
            "src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts",
            new=AsyncMock(return_value=[generated_post]),
        ),
        patch(
            "src.api.v1.linkedin.OutreachSequenceGenerator.generate_sequence",
            new=AsyncMock(return_value=outreach),
        ),
        patch("src.api.v1.linkedin.BaseRepository", return_value=repository),
        pytest.raises(HTTPException) as error,
    ):
        await generate_campaign_content(campaign_id, user=user)

    assert error.value.status_code == 503
    assert client.calls[0][0] == "replace_linkedin_campaign_content"


@pytest.mark.asyncio
async def test_existing_ownership_boundary_runs_before_generation_or_persistence() -> None:
    campaign_id = uuid4()
    user = AuthenticatedUser(id=str(uuid4()), roles=["user"], permissions=[])
    generate_posts = AsyncMock()
    repository = SimpleNamespace(client=_Client(data={}))

    with (
        patch(
            "src.api.v1.linkedin.CampaignContextResolver.resolve",
            new=AsyncMock(side_effect=HTTPException(404, "Campaign not found or access denied.")),
        ),
        patch(
            "src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts",
            new=generate_posts,
        ),
        patch("src.api.v1.linkedin.BaseRepository", return_value=repository),
        pytest.raises(HTTPException) as error,
    ):
        await generate_campaign_content(campaign_id, user=user)

    assert error.value.status_code == 404
    generate_posts.assert_not_awaited()
    assert repository.client.calls == []


def test_forward_migration_defines_one_atomic_owned_replacement() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "migrations"
        / "013_replace_linkedin_campaign_content_rpc.up.sql"
    ).read_text(encoding="utf-8").lower()

    assert "create or replace function public.replace_linkedin_campaign_content" in migration
    assert "security invoker" in migration
    assert "organization_id = p_user_id" in migration
    assert "for update" in migration
    assert "delete from public.linkedin_posts" in migration
    assert "delete from public.outreach_sequences" in migration
    assert "insert into public.linkedin_posts" in migration
    assert "insert into public.outreach_sequences" in migration
    assert "grant execute" in migration
    assert "drop table" not in migration
    assert "truncate" not in migration


@pytest.mark.asyncio
async def test_canonical_brand_context_propagates_to_real_sequence_generator_and_persists() -> None:
    campaign_id, user, inputs, plan, generated_post, _ = _context()
    database_post_id = uuid4()
    database_sequence_id = uuid4()
    payload = {
        "posts": [
            {
                **generated_post.to_dict(),
                "id": str(database_post_id),
                "campaign_id": str(campaign_id),
            }
        ],
        "sequence": {
            "id": str(database_sequence_id),
            "campaign_id": str(campaign_id),
        },
    }
    client = _Client(data=payload)
    repository = SimpleNamespace(client=client)

    mock_llm_json = AsyncMock(
        return_value={
            "step_invite_msg": "Hi Alex, saw your work on autonomous pipelines.",
            "step_value_msg": "Hi Alex, thought this benchmark on data pipelines could help.",
            "step_followup_msg": "Hi Alex, just following up.",
        }
    )

    with (
        patch(
            "src.api.v1.linkedin.CampaignContextResolver.resolve",
            new=AsyncMock(return_value=inputs),
        ),
        patch(
            "src.api.v1.linkedin.PlanRefinementService.get_plan",
            new=AsyncMock(return_value=plan),
        ),
        patch(
            "src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts",
            new=AsyncMock(return_value=[generated_post]),
        ),
        patch(
            "src.modules.linkedin.generators.sequence_generator.LLMRouterService.generate_json",
            new=mock_llm_json,
        ),
        patch("src.api.v1.linkedin.BaseRepository", return_value=repository),
    ):
        response = await generate_campaign_content(campaign_id, user=user)

    assert response["status"] == "success"
    assert response["sequence_generated"] is True

    # Verify that the REAL generate_sequence received inputs.brand and formatted it into prompt
    mock_llm_json.assert_awaited_once()
    _, user_prompt = mock_llm_json.call_args[0]
    assert "BRAND IDENTITY AND REQUIRED COMMUNICATION RULES:" in user_prompt
    assert "Task 8 Brand" in user_prompt
    assert "Never use buzzwords" in user_prompt

    # Verify successful generation continues to the existing atomic persistence path
    assert client.calls[0][0] == "replace_linkedin_campaign_content"
    rpc_args = client.calls[0][1]
    assert rpc_args["p_sequence"]["step_invite_msg"] == "Hi Alex, saw your work on autonomous pipelines."


@pytest.mark.asyncio
async def test_outreach_sequence_failure_prevents_partial_persistence() -> None:
    campaign_id, user, inputs, plan, generated_post, _ = _context()
    client = _Client(data={})
    repository = SimpleNamespace(client=client)

    mock_llm_json = AsyncMock(side_effect=RuntimeError("LLM outreach service error"))

    with (
        patch(
            "src.api.v1.linkedin.CampaignContextResolver.resolve",
            new=AsyncMock(return_value=inputs),
        ),
        patch(
            "src.api.v1.linkedin.PlanRefinementService.get_plan",
            new=AsyncMock(return_value=plan),
        ),
        patch(
            "src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts",
            new=AsyncMock(return_value=[generated_post]),
        ),
        patch(
            "src.modules.linkedin.generators.sequence_generator.LLMRouterService.generate_json",
            new=mock_llm_json,
        ),
        patch("src.api.v1.linkedin.BaseRepository", return_value=repository),
        pytest.raises(HTTPException) as exc_info,
    ):
        await generate_campaign_content(campaign_id, user=user)

    assert exc_info.value.status_code == 502
    assert "LinkedIn generation failed. Please retry." in exc_info.value.detail
    # Verify atomic persistence was NEVER called, preventing partial post persistence
    assert client.calls == []


@pytest.mark.asyncio
async def test_app_launch_outreach_neutrality() -> None:
    campaign_id, user, inputs, plan, generated_post, _ = _context()
    inputs.campaign.goals = SimpleNamespace(primary="App user acquisition")
    inputs.intake = {
        "campaign_type": "app_launch",
        "campaign_name": "GlowBook Launch",
        "objective": "Acquire 10,000 app downloads",
        "value_proposition": "Smart ledger for independent creators",
        "cta_url": "https://glowbook.app/download",
        "updated_at": "2026-09-17T10:05:00+00:00",
    }
    plan = plan.model_copy(
        update={
            "input_identity": InputIdentity(
                campaign_id=campaign_id,
                company_profile_id=inputs.brand.company_profile_id,
                brand_version=compute_brand_fingerprint(inputs.brand),
                intake_hash=compute_intake_fingerprint(inputs.intake, inputs.campaign),
            )
        }
    )
    for forbidden in ("venue", "guest_name", "curriculum", "seats", "attendee_outcome"):
        assert forbidden not in inputs.intake

    client = _Client(data={"posts": [{"id": str(uuid4())}], "sequence": {"id": str(uuid4())}})
    repository = SimpleNamespace(client=client)

    mock_llm_json = AsyncMock(
        return_value={
            "step_invite_msg": "Hi [Name], loved your creator content.",
            "step_value_msg": "Hi [Name], sharing GlowBook smart ledger.",
            "step_followup_msg": "Hi [Name], quick follow up.",
        }
    )

    with (
        patch(
            "src.api.v1.linkedin.CampaignContextResolver.resolve",
            new=AsyncMock(return_value=inputs),
        ),
        patch(
            "src.api.v1.linkedin.PlanRefinementService.get_plan",
            new=AsyncMock(return_value=plan),
        ),
        patch(
            "src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts",
            new=AsyncMock(return_value=[generated_post]),
        ),
        patch(
            "src.modules.linkedin.generators.sequence_generator.LLMRouterService.generate_json",
            new=mock_llm_json,
        ),
        patch("src.api.v1.linkedin.BaseRepository", return_value=repository),
    ):
        response = await generate_campaign_content(campaign_id, user=user)

    assert response["status"] == "success"
    assert client.calls[0][0] == "replace_linkedin_campaign_content"

