"""Focused regression coverage for the active structured LLM contract."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from src.models.llm import LLMResponse, TokenUsage
from src.modules.planning.agents import panel
from src.modules.planning.models.brief import PlanBrief
from src.modules.research.services.llm_router import (
    LLMRouterError,
    LLMRouterService,
)

_RESPONSES = {
    "plan_audience_research": {
        "objective": "Launch GlowBook",
        "smart_goals": [],
        "personas": [],
    },
    "plan_positioning": {
        "positioning_statement": "Book trusted beauty appointments quickly.",
        "messaging_pillars": ["Convenience"],
    },
    "plan_channel": {
        "platforms": [{"platform": "linkedin"}],
        "phases": [],
        "calendar_slots": [],
    },
    "plan_measurement": {
        "kpis": [{"name": "Downloads", "target": "100"}],
    },
    "plan_competitive": {
        "landscape": [],
        "differentiation_angle": "Local salon availability.",
    },
}


class FakeCanonicalLLM:
    def __init__(self, response_text: str | None = None) -> None:
        self.response_text = response_text
        self.requests = []

    def is_local_ollama(self) -> bool:
        return False

    def has_ollama_provider(self) -> bool:
        return False

    def generate(self, request):
        self.requests.append(request)
        payload = self.response_text or json.dumps(_RESPONSES[request.prompt_name])
        return LLMResponse(
            text=payload,
            token_usage=TokenUsage(),
            provider="test",
            model="test",
        )


@pytest.mark.asyncio
async def test_all_five_specialists_use_canonical_generate_contract() -> None:
    llm = FakeCanonicalLLM()
    brief = PlanBrief(user_goal="Launch GlowBook", campaign_name="GlowBook")

    with (
        patch.object(panel, "_parallel_research", new=AsyncMock(return_value="evidence")),
        patch.object(
            panel,
            "_parallel_competitor_research",
            new=AsyncMock(return_value="evidence"),
        ),
    ):
        results = {
            name: await specialist(brief, llm=llm) for name, specialist in panel.SPECIALISTS.items()
        }

    assert set(results) == set(panel.SPECIALISTS)
    assert len(llm.requests) == 5
    assert all(request.json_mode for request in llm.requests)
    assert all(request.max_tokens and request.max_tokens <= 2400 for request in llm.requests)


@pytest.mark.asyncio
async def test_research_router_parses_fenced_json_through_canonical_service() -> None:
    llm = FakeCanonicalLLM('```json\n{"queries": ["one", "two"]}\n```')

    result = await LLMRouterService(llm=llm).generate_json("system", "user")

    assert result == {"queries": ["one", "two"]}
    assert llm.requests[0].json_mode is True


@pytest.mark.asyncio
async def test_research_router_rejects_invalid_structured_output() -> None:
    router = LLMRouterService(llm=FakeCanonicalLLM("not JSON"))

    with pytest.raises(LLMRouterError, match="Structured LLM generation failed"):
        await router.generate_json("system", "user")


@pytest.mark.asyncio
async def test_specialist_response_is_validated_against_its_schema() -> None:
    llm = FakeCanonicalLLM('{"personas": [{"name": {"invalid": true}}]}')

    with pytest.raises(ValidationError):
        await panel.ask_json(
            "plan_audience_research",
            PlanBrief(user_goal="Launch GlowBook").as_prompt_vars(),
            llm=llm,
        )
