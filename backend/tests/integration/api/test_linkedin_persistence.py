import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.main import app
from src.modules.linkedin.models import LinkedInPost, OutreachTemplate, PostStatus

pytestmark = pytest.mark.asyncio

USER_A_ID = "dbf46eb4-fa7d-4d1a-92f3-57caafea41b9"


def mock_user_a() -> AuthenticatedUser:
    return AuthenticatedUser(id=USER_A_ID, roles=["user"], permissions=[])


@pytest.fixture
def user_a_client() -> Generator[AsyncClient]:
    import httpx

    app.dependency_overrides[get_authenticated_user] = mock_user_a
    transport = httpx.ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()


@patch("src.api.v1.linkedin.check_plan_freshness", return_value=(False, None))
@patch("src.api.v1.linkedin.LinkedInPostGenerator.generate_all_posts")
@patch("src.api.v1.linkedin.OutreachSequenceGenerator.generate_sequence")
@patch("src.api.v1.linkedin.PlanRefinementService.get_plan")
async def test_linkedin_generation_persistence(
    mock_get_plan, mock_outreach, mock_posts, mock_freshness, user_a_client
):
    mock_posts.return_value = [
        LinkedInPost(
            campaign_id=uuid.uuid4(),
            slot_id="1",
            scheduled_at=datetime.now(UTC),
            hook="Hook",
            body="Body",
            cta_text="CTA",
            full_content="Full",
            status=PostStatus.DRAFT,
        )
    ]
    mock_outreach.return_value = OutreachTemplate(
        campaign_id=uuid.uuid4(), step_invite_msg="Invite"
    )

    from types import SimpleNamespace

    from src.modules.planning.models.campaign_plan import CalendarSlot, CampaignPlan, ChannelPlan
    from src.repositories.base import BaseRepository

    class MockRepo:
        def __init__(self, table_name: str):
            self.table_name = table_name
            self._real = BaseRepository(table_name)

        @property
        def client(self):
            real_client = self._real.client

            class ClientWrapper:
                def __getattr__(self, name):
                    return getattr(real_client, name)

                def rpc(self, rpc_name, args):
                    if rpc_name == "replace_linkedin_campaign_content":
                        c_id = args["p_campaign_id"]
                        real_client.table("linkedin_posts").delete().eq(
                            "campaign_id", c_id
                        ).execute()
                        real_client.table("outreach_sequences").delete().eq(
                            "campaign_id", c_id
                        ).execute()
                        seq_record = {**args["p_sequence"], "campaign_id": c_id}
                        inserted_seq = (
                            real_client.table("outreach_sequences")
                            .insert(seq_record)
                            .execute()
                            .data[0]
                        )
                        posts_to_insert = [{**p, "campaign_id": c_id} for p in args["p_posts"]]
                        inserted_posts = (
                            real_client.table("linkedin_posts")
                            .insert(posts_to_insert)
                            .execute()
                            .data
                        )
                        return SimpleNamespace(
                            execute=lambda: SimpleNamespace(
                                data={"posts": inserted_posts, "sequence": inserted_seq}
                            )
                        )
                    return real_client.rpc(rpc_name, args)

            return ClientWrapper()

    with patch("src.api.v1.linkedin.BaseRepository", new=MockRepo):
        client = user_a_client

        # 1. Create company profile
        res = await client.post(
            "/api/v1/company",
            json={
                "company_name": f"Test Company {uuid.uuid4().hex[:8]}",
                "industry": "Software",
                "description": "A testing company.",
                "target_audience": "Developers",
                "key_value_proposition": "Testing",
                "brand_tone": "Professional",
                "brand_guidelines": "No guidelines",
            },
        )
        assert res.status_code == 201, res.text
        profile_id = res.json()["id"]

        # 2. Create Campaign
        res = await client.post(
            "/api/v1/campaigns",
            json={
                "name": f"Test Persistence Campaign {uuid.uuid4().hex[:8]}",
                "company_profile_id": profile_id,
                "type": "event",
                "platforms": ["LinkedIn"],
                "goals": {"primary": "Testing"},
                "target_audience": {"segments": []},
                "schedule": {
                    "start_date": "2026-10-01T00:00:00Z",
                    "end_date": "2026-10-31T00:00:00Z",
                    "timezone": "UTC",
                },
            },
        )
        assert res.status_code == 201, res.text
        campaign_id = res.json()["id"]

        # 3. (Skipped: intake is handled gracefully if missing)
        mock_plan = CampaignPlan(
            campaign_id=uuid.UUID(campaign_id),
            status="Approved",
            channel_plan=ChannelPlan(
                calendar_slots=[
                    CalendarSlot(slot_id="dummy", date="2026-10-10", theme="Test", cta="Test")
                ]
            ),
        )
        mock_get_plan.return_value = mock_plan

        # 5. Generate linkedin content
        res = await client.post(f"/api/v1/linkedin/campaigns/{campaign_id}/generate", json={})
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "success"
        assert data["posts_generated"] > 0
        assert "posts" in data

        posts = data["posts"]
        post_ids = [p["id"] for p in posts]

        # 6. Verify retrieved posts match saved IDs
        res = await client.get(f"/api/v1/linkedin/campaigns/{campaign_id}/preview")
        assert res.status_code == 200, res.text
        preview_data = res.json()

        saved_posts = preview_data["posts"]
        saved_ids = [p["id"] for p in saved_posts]

        assert set(post_ids) == set(saved_ids)
