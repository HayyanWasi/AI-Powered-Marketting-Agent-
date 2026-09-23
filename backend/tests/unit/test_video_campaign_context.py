from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import unquote
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.agents.video_script_agent import VideoScriptAgent
from src.api.dependencies import get_authenticated_user
from src.models.brand_context import BrandContext
from src.models.campaign import Campaign, Goals, Schedule
from src.models.video_generation_context import VideoGenerationContext
from src.modules.planning.models.campaign_plan import (
    CampaignPlan,
    CoreStrategy,
    InputIdentity,
    ResearchStatus,
)
from src.services.campaign_context_service import (
    CampaignContextResolver,
    CampaignInputs,
    check_plan_freshness,
    compute_brand_fingerprint,
    compute_intake_fingerprint,
)
from src.services.video_generation_service import VideoGenerationError, VideoGenerationService


def _context(*, event: bool = False) -> VideoGenerationContext:
    owner_id = uuid4()
    campaign_id = uuid4()
    name = "NovaCare Community Health Day" if event else "GlowBook"
    campaign = Campaign(
        id=campaign_id,
        organization_id=owner_id,
        company_profile_id=uuid4(),
        name=name,
        goals=Goals(primary="Community education" if event else "Acquire app downloads"),
        schedule=Schedule(
            start_date=datetime.now(UTC) + timedelta(days=1),
            end_date=datetime.now(UTC) + timedelta(days=14),
            timezone="Asia/Karachi",
        ),
        created_by=owner_id,
        updated_by=owner_id,
    )
    brand = BrandContext(
        company_profile_id=campaign.company_profile_id,
        company_name="NovaCare Hospital" if event else "GlowBook",
        description=(
            "Trusted hospital preventive-care programs"
            if event
            else "A mobile beauty booking application"
        ),
        target_audience="Local families" if event else "Urban women seeking beauty services",
        brand_tone="Calm and medically responsible" if event else "Confident and uplifting",
        personality_traits=("trustworthy", "clear") if event else ("modern", "warm"),
        negative_guardrails=(
            "Never promise medical outcomes" if event else "Never shame appearance",
        ),
        reference_image_urls=("https://assets.invalid/reference.jpg",),
    )
    intake = {
        "campaign_type": "physical_event" if event else "app_launch",
        "campaign_name": name,
        "objective": "Community preventive-care awareness" if event else "Acquire app downloads",
        "target_audience": "Local patients and families" if event else "Urban women ages 20-40",
        "value_proposition": (
            "Practical preventive-care education"
            if event
            else "Book trusted beauty services in minutes"
        ),
        "cta_url": "https://novacare.invalid/health-day" if event else "https://glowbook.app/download",
    }
    if event:
        intake.update(
            {
                "event_date": "2026-11-12",
                "venue": "NovaCare Community Hall",
                "has_guest": True,
                "guest_name": "Dr. Amina Shah",
                "guest_title": "Preventive Care Lead",
            }
        )
    plan = CampaignPlan(
        campaign_id=campaign_id,
        version=3,
        research_status=ResearchStatus.AVAILABLE,
        source_brief={"research_context": {"verified_finding": "Audience values convenience"}},
        core_strategy=CoreStrategy(
            positioning_statement="The trusted practical choice",
            unique_selling_proposition=intake["value_proposition"],
            messaging_pillars=("trust", "convenience"),
            tone_of_voice=brand.brand_tone,
        ),
    )
    return VideoGenerationContext.from_sources(
        inputs=CampaignInputs(campaign, brand, intake),
        plan=plan,
        owner_id=owner_id,
        user_instruction="Create an awareness video",
    )


class _CapturingLLM:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.request = None

    def generate(self, request):
        self.request = request
        return SimpleNamespace(text=self.payload)


def _five_scenes(identity: str = "GlowBook") -> str:
    return "[" + ",".join(
        f'{{"scene_number":{number},"narration":"Clear trusted value today","image_prompt":"{identity} consistent branded product scene"}}'
        for number in range(1, 6)
    ) + "]"


@pytest.mark.asyncio
async def test_glowbook_script_receives_canonical_context_without_event_assumptions() -> None:
    context = _context()
    llm = _CapturingLLM(_five_scenes())
    agent = VideoScriptAgent()
    agent.llm = llm

    scenes = await agent.generate_script(context)
    prompt = llm.request.user_prompt

    assert len(scenes) == 5
    assert "GlowBook" in prompt
    assert "Urban women ages 20-40" in prompt
    assert "https://glowbook.app/download" in prompt
    assert "Never shame appearance" in prompt
    assert "Create an awareness video" in prompt
    assert "Event date:" not in context.campaign_facts_prompt()
    assert context.reference_images_used is False


@pytest.mark.asyncio
async def test_novacare_script_receives_only_supplied_event_facts() -> None:
    context = _context(event=True)
    llm = _CapturingLLM(_five_scenes("NovaCare Hospital"))
    agent = VideoScriptAgent()
    agent.llm = llm

    await agent.generate_script(context)
    prompt = llm.request.user_prompt

    assert "NovaCare Hospital" in prompt
    assert "2026-11-12" in prompt
    assert "NovaCare Community Hall" in prompt
    assert "Dr. Amina Shah" in prompt
    assert "Never promise medical outcomes" in prompt
    assert "GlowBook" not in prompt
    assert "Do not invent absent event facts:" in prompt
    assert "ticket price" in prompt
    assert "seat count" in prompt


@pytest.mark.asyncio
async def test_script_rejects_invalid_scene_count() -> None:
    llm = _CapturingLLM(
        '[{"scene_number":1,"narration":"Only one scene here","image_prompt":"one image"}]'
    )
    agent = VideoScriptAgent()
    agent.llm = llm

    with pytest.raises(ValueError, match="exactly five scenes"):
        await agent.generate_script(_context())


@pytest.mark.asyncio
async def test_llm_failure_propagates_without_fake_script() -> None:
    class FailingLLM:
        def generate(self, _request):
            raise RuntimeError("provider unavailable")

    agent = VideoScriptAgent()
    agent.llm = FailingLLM()

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await agent.generate_script(_context())


@pytest.mark.asyncio
async def test_app_launch_rejects_invented_event_language() -> None:
    payload = _five_scenes().replace("Clear trusted value today", "Register now for workshop")
    agent = VideoScriptAgent()
    agent.llm = _CapturingLLM(payload)

    with pytest.raises(ValueError, match="invented unsupported campaign details"):
        await agent.generate_script(_context())


@pytest.mark.asyncio
async def test_image_prompt_includes_shared_context(monkeypatch) -> None:
    captured_urls: list[str] = []

    class Response:
        status_code = 200
        content = b"x" * 2001

    class Client:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def get(self, url, **_kwargs):
            captured_urls.append(url)
            return Response()

    monkeypatch.setattr("src.services.video_generation_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("src.services.video_generation_service.settings.cloudflare_account_id", "")
    monkeypatch.setattr("src.services.video_generation_service.settings.cloudflare_ai_token", "")
    service = object.__new__(VideoGenerationService)
    monkeypatch.setattr(service, "_crop_and_resize_to_720_1280", lambda _path: None)
    monkeypatch.setattr(Path, "write_bytes", lambda _path, _content: 2001)

    await service._generate_scenery(
        "woman confidently books a beauty appointment",
        _context(),
        Path("unused"),
        0,
        5,
    )

    decoded = unquote(captured_urls[0])
    assert "GlowBook" in decoded
    assert "Urban women ages 20-40" in decoded
    assert "Never shame appearance" in decoded
    assert "woman confidently books a beauty appointment" in decoded


@pytest.mark.asyncio
async def test_all_image_provider_failures_abort_without_fake_frame(monkeypatch) -> None:
    class Response:
        status_code = 503
        content = b""

    class Client:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def get(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr("src.services.video_generation_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("src.services.video_generation_service.settings.cloudflare_account_id", "")
    monkeypatch.setattr("src.services.video_generation_service.settings.cloudflare_ai_token", "")
    service = object.__new__(VideoGenerationService)
    writes: list[bytes] = []
    monkeypatch.setattr(Path, "write_bytes", lambda _path, content: writes.append(content))

    with pytest.raises(VideoGenerationError, match="All configured image providers failed"):
        await service._generate_scenery("scene", _context(), Path("unused"), 1, 5)
    assert writes == []


@pytest.mark.asyncio
async def test_anonymous_video_request_is_denied_by_active_auth_dependency() -> None:
    with pytest.raises(HTTPException) as exc:
        await get_authenticated_user(authorization=None, x_user_id=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_foreign_campaign_is_denied_by_canonical_resolver() -> None:
    campaign_id = uuid4()
    user_id = uuid4()
    get_by_id = AsyncMock(return_value=None)

    with patch("src.services.campaign_context_service.CampaignRepository") as repo_cls:
        repo_cls.return_value.get_by_id = get_by_id
        with pytest.raises(HTTPException) as exc:
            await CampaignContextResolver().resolve(campaign_id, str(user_id))

    assert exc.value.status_code == 404
    get_by_id.assert_awaited_once_with(campaign_id, user_id)


def test_video_uses_existing_freshness_identity_for_changed_campaign_facts() -> None:
    context = _context()
    campaign = SimpleNamespace(
        id=context.campaign_id,
        name=context.campaign_name,
        company_profile_id=context.brand.company_profile_id,
        platforms=["LinkedIn"],
        goals=SimpleNamespace(primary=context.objective),
        schedule=SimpleNamespace(start_date=None, end_date=None, timezone="UTC"),
    )
    intake = {
        "campaign_type": context.campaign_type,
        "campaign_name": context.campaign_name,
        "objective": context.objective,
        "target_audience": context.target_audience,
        "value_proposition": context.value_proposition,
        "cta_url": context.cta_url,
    }
    plan = CampaignPlan(
        campaign_id=context.campaign_id,
        input_identity=InputIdentity(
            campaign_id=context.campaign_id,
            company_profile_id=context.brand.company_profile_id,
            brand_version=compute_brand_fingerprint(context.brand),
            intake_hash=compute_intake_fingerprint(intake, campaign),
        ),
    )
    changed = dict(intake, objective="Acquire paid subscriptions")

    is_stale, reason = check_plan_freshness(
        plan,
        CampaignInputs(campaign=campaign, brand=context.brand, intake=changed),
    )

    assert is_stale is True
    assert reason == "Campaign details were updated."
