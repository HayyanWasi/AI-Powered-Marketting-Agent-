import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.modules.planning.agents.panel import (
    planning_specialist_concurrency,
    planning_timeout_seconds,
    run_panel,
)
from src.modules.planning.models.brief import PlanBrief


def _llm(is_ollama: bool) -> MagicMock:
    svc = MagicMock()
    svc.is_local_ollama.return_value = is_ollama
    svc.has_ollama_provider.return_value = is_ollama
    return svc


async def _observe_max_concurrency(llm) -> int:
    brief = PlanBrief(user_goal="Test Goal")
    active = 0
    max_active = 0

    async def mock_specialist(brief, **kw):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.02)
        active -= 1
        return {"data": "success"}

    with patch(
        "src.modules.planning.agents.panel.SPECIALISTS",
        {f"spec_{i}": mock_specialist for i in range(5)},
    ):
        results = await run_panel(brief, llm=llm)

    assert len(results) == 5
    return max_active


# ── A. Ollama planning specialists never exceed concurrency 1 ──
@pytest.mark.asyncio
async def test_ollama_panel_concurrency_is_one():
    assert planning_specialist_concurrency(_llm(True)) == 1
    assert await _observe_max_concurrency(_llm(True)) == 1


# ── B. Remote planning preserves intended concurrency 2 ──
@pytest.mark.asyncio
async def test_remote_panel_concurrency_is_two():
    assert planning_specialist_concurrency(_llm(False)) == 2
    assert await _observe_max_concurrency(_llm(False)) == 2


# ── C. Ollama uses the 180s planning timeout; remote does not ──
def test_planning_timeout_policy():
    assert planning_timeout_seconds(_llm(True)) == 180.0
    assert planning_timeout_seconds(_llm(False)) is None


@pytest.mark.asyncio
async def test_terminal_failure_propagates_and_cancels_siblings():
    brief = PlanBrief(user_goal="Test Goal")

    async def fast_fail(brief, **kw):
        await asyncio.sleep(0.01)
        raise RuntimeError("Terminal failure!")

    async def slow(brief, **kw):
        try:
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            return {"status": "cancelled"}
        return {"status": "success"}

    with patch(
        "src.modules.planning.agents.panel.SPECIALISTS",
        {"fail": fast_fail, "slow1": slow, "slow2": slow, "slow3": slow, "slow4": slow},
    ):
        with pytest.raises(RuntimeError, match="Terminal failure"):
            await run_panel(brief, llm=_llm(False))
