"""Three-lane planning execution: routing, isolation, concurrency, fallback.

Lane A (Ollama A) → channel_plan; Lane B (Ollama B) → measurement, positioning;
Lane C (remote) → audience_research, competitive. Chief runs after all five,
preferring Lane A with remote fallback.
"""

from __future__ import annotations

import asyncio

import pytest

from src.modules.planning.models.brief import PlanBrief
from src.modules.workflow_engine.graphs import campaign_plan as g
from src.services import llm_service


# ── A/B/C. specialist → lane assignment ──
def test_lane_assignment():
    assert g._LANE_ASSIGNMENT["channel_plan"] == "A"
    assert g._LANE_ASSIGNMENT["measurement"] == "B"
    assert g._LANE_ASSIGNMENT["positioning"] == "B"
    assert g._LANE_ASSIGNMENT["audience_research"] == "C"
    assert g._LANE_ASSIGNMENT["competitive"] == "C"


def test_lane_services_shape(monkeypatch):
    # Legacy (LLM_MODE=ollama) rollback shape: A/B are Ollama-primary. The
    # default remote mode (covered by test_lane_services_remote_mode) routes all
    # lanes to the remote chain regardless of the configured A/B URLs.
    monkeypatch.setattr(llm_service.settings, "llm_mode", "ollama")
    monkeypatch.setattr(llm_service.settings, "planning_ollama_a_base_url", "http://a/v1")
    monkeypatch.setattr(llm_service.settings, "planning_ollama_b_base_url", "http://b/v1")
    svcs = g._build_lane_services()
    # A and B are Ollama-primary with remote fallback; C is remote-only.
    assert [c[0] for c in svcs["A"]._chain][0] == "ollama"
    assert svcs["A"].has_ollama_provider()
    assert svcs["B"].has_ollama_provider()
    assert not svcs["C"].has_ollama_provider()
    # A and B point at different endpoints (no shared GPU).
    assert svcs["A"]._chain[0][1] is not svcs["B"]._chain[0][1]


def test_lane_services_remote_mode(monkeypatch):
    # Default remote-only mode: even with A/B Ollama URLs configured, every lane
    # is the remote chain and no lane carries an Ollama provider.
    monkeypatch.setattr(llm_service.settings, "llm_mode", "remote")
    monkeypatch.setattr(llm_service.settings, "planning_ollama_a_base_url", "http://a/v1")
    monkeypatch.setattr(llm_service.settings, "planning_ollama_b_base_url", "http://b/v1")
    svcs = g._build_lane_services()
    for lane in ("A", "B", "C"):
        assert not svcs[lane].has_ollama_provider()
        assert "ollama" not in [c[0] for c in svcs[lane]._chain]


# ── E/F. an Ollama lane gate never exceeds one active request ──
@pytest.mark.asyncio
async def test_lane_gate_concurrency_one():
    gate = g._LaneGate("A", 1)
    observed = []

    async def work():
        observed.append(gate.active)
        await asyncio.sleep(0.02)

    await asyncio.gather(*[gate.run(f"s{i}", "ollama", work) for i in range(4)])
    assert gate.max_active == 1


@pytest.mark.asyncio
async def test_remote_lane_allows_two():
    gate = g._LaneGate("C", g._REMOTE_LANE_CONCURRENCY)

    async def work():
        await asyncio.sleep(0.03)

    await asyncio.gather(*[gate.run(f"s{i}", "remote", work) for i in range(4)])
    assert gate.max_active == 2


# ── D. lanes execute concurrently (A, B, C overlap in time) ──
@pytest.mark.asyncio
async def test_lanes_run_concurrently():
    brief = PlanBrief(user_goal="x")

    active_lanes_peak = {"n": 0}
    live = set()

    async def fake_specialist_factory(name):
        async def fn(b, **kw):
            live.add(g._LANE_ASSIGNMENT[name])
            active_lanes_peak["n"] = max(active_lanes_peak["n"], len(live))
            await asyncio.sleep(0.05)
            live.discard(g._LANE_ASSIGNMENT[name])
            return {"data": name}

        return fn

    specialists = {n: (await fake_specialist_factory(n)) for n in g._LANE_ASSIGNMENT}

    import unittest.mock as m

    with (
        m.patch.object(g, "SPECIALISTS", specialists),
        m.patch.object(g.chief_strategist, "synthesize", new=_fake_synth),
    ):
        graph = g.compile_graph()
        state = await graph.ainvoke(g.initial_state(brief))

    # Three lanes should be active simultaneously at the peak.
    assert active_lanes_peak["n"] == 3
    assert len(state["sections"]) == 5


async def _fake_synth(brief, panel, **kw):
    from src.modules.planning.agents.chief_strategist import assemble

    return assemble(panel, title="t", executive_summary="e")


# ── G. local timeout → remote fallback, no same-Ollama retry ──
def test_ollama_timeout_falls_back_to_remote_not_retry():
    from unittest.mock import MagicMock, patch

    from src.models.llm import LLMRequest, LLMResponse, TokenUsage
    from src.services.llm_service import LLMService

    class APITimeoutError(Exception):
        pass

    svc = LLMService.planning_ollama_lane("http://a/v1", "qwen3:8b")
    ollama = MagicMock()
    ollama.generate.side_effect = APITimeoutError("Request timed out.")
    remote = MagicMock()
    remote.generate.return_value = LLMResponse(
        text="{}",
        token_usage=TokenUsage(0, 0, 0, "gemini"),
        provider="gemini",
        model="g",
        finish_reason="stop",
    )
    svc._chain = [("ollama", ollama, "qwen3:8b"), ("gemini", remote, "g")]

    with patch("src.services.llm_service.time.sleep"):
        resp = svc.generate(LLMRequest(user_prompt="x", timeout=180.0))

    assert ollama.generate.call_count == 1  # no same-Ollama retry
    assert remote.generate.call_count == 1  # fell back to remote
    assert resp.provider == "gemini"


# ── K. chief runs only after all five specialists complete ──
@pytest.mark.asyncio
async def test_chief_runs_after_all_specialists():
    brief = PlanBrief(user_goal="x")
    completed = []

    async def make(name):
        async def fn(b, **kw):
            await asyncio.sleep(0.02)
            completed.append(name)
            return {"data": name}

        return fn

    specialists = {n: (await make(n)) for n in g._LANE_ASSIGNMENT}

    seen_at_synth = {}

    async def synth(brief, panel, **kw):
        seen_at_synth["count"] = len(panel)
        from src.modules.planning.agents.chief_strategist import assemble

        return assemble(panel, title="t", executive_summary="e")

    import unittest.mock as m

    with (
        m.patch.object(g, "SPECIALISTS", specialists),
        m.patch.object(g.chief_strategist, "synthesize", new=synth),
    ):
        await g.compile_graph().ainvoke(g.initial_state(brief))

    assert seen_at_synth["count"] == 5  # all five present before chief ran
