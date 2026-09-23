"""Planning Ollama warm-up: once, concurrency-safe, no fake readiness, isolated."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from src.modules.planning import warmup


@pytest.fixture(autouse=True)
def _clean_warm_state():
    warmup.reset()
    warmup._locks.clear()
    yield
    warmup.reset()
    warmup._locks.clear()


class _CountingOllama:
    """Stands in for OllamaProvider.generate, counting calls per base URL."""

    calls: dict[str, int] = {}

    def __init__(self, base_url=None, model=None, **kw):
        self.base_url = base_url

    def generate(self, *a, **kw):
        _CountingOllama.calls[self.base_url] = _CountingOllama.calls.get(self.base_url, 0) + 1
        return None


def _config(monkeypatch, a="http://a/v1", b="http://b/v1"):
    monkeypatch.setattr(warmup.settings, "planning_ollama_a_base_url", a)
    monkeypatch.setattr(warmup.settings, "planning_ollama_b_base_url", b)
    monkeypatch.setattr(warmup.settings, "planning_ollama_a_model", "qwen3:8b")
    monkeypatch.setattr(warmup.settings, "planning_ollama_b_model", "qwen3:8b")


# ── A. A and B each warm exactly once under normal init ──
@pytest.mark.asyncio
async def test_each_endpoint_warms_once(monkeypatch):
    _CountingOllama.calls = {}
    _config(monkeypatch)
    with patch.object(warmup, "OllamaProvider", _CountingOllama):
        r1 = await warmup.ensure_planning_endpoints_warm()
        r2 = await warmup.ensure_planning_endpoints_warm()  # idempotent second call
    assert r1 == {"A": True, "B": True}
    assert r2 == {"A": True, "B": True}
    assert _CountingOllama.calls == {"http://a/v1": 1, "http://b/v1": 1}


# ── B. concurrent requests cannot trigger duplicate warm-ups ──
@pytest.mark.asyncio
async def test_concurrent_warmups_are_deduped(monkeypatch):
    _CountingOllama.calls = {}
    _config(monkeypatch)

    class _SlowOllama(_CountingOllama):
        def generate(self, *a, **kw):
            import time
            _CountingOllama.calls[self.base_url] = _CountingOllama.calls.get(self.base_url, 0) + 1
            time.sleep(0.05)
            return None

    with patch.object(warmup, "OllamaProvider", _SlowOllama):
        await asyncio.gather(*[warmup.ensure_planning_endpoints_warm() for _ in range(5)])
    assert _CountingOllama.calls == {"http://a/v1": 1, "http://b/v1": 1}


# ── C. successful warm-up marks that endpoint ready ──
@pytest.mark.asyncio
async def test_success_marks_ready(monkeypatch):
    _CountingOllama.calls = {}
    _config(monkeypatch)
    with patch.object(warmup, "OllamaProvider", _CountingOllama):
        await warmup.ensure_planning_endpoints_warm()
    assert warmup.is_warm("http://a/v1")
    assert warmup.is_warm("http://b/v1")


# ── D. failed warm-up does not fake readiness (and E: retried next time) ──
@pytest.mark.asyncio
async def test_failure_does_not_mark_ready_and_retries(monkeypatch):
    _config(monkeypatch)

    class _FailingOllama:
        attempts = 0

        def __init__(self, base_url=None, model=None, **kw):
            self.base_url = base_url

        def generate(self, *a, **kw):
            _FailingOllama.attempts += 1
            raise RuntimeError("Request timed out.")

    with patch.object(warmup, "OllamaProvider", _FailingOllama):
        result = await warmup.ensure_planning_endpoints_warm()
        assert result == {"A": False, "B": False}
        assert not warmup.is_warm("http://a/v1")
        # E: a subsequent call retries (not permanently marked ready/unready)
        before = _FailingOllama.attempts
        await warmup.ensure_planning_endpoints_warm()
        assert _FailingOllama.attempts > before


# ── E(pt2). failure still permits planning (no exception raised) ──
@pytest.mark.asyncio
async def test_warmup_never_raises(monkeypatch):
    _config(monkeypatch)

    class _Boom:
        def __init__(self, **kw):
            self.base_url = kw.get("base_url")

        def generate(self, *a, **kw):
            raise ConnectionError("down")

    with patch.object(warmup, "OllamaProvider", _Boom):
        result = await warmup.ensure_planning_endpoints_warm()  # must not raise
    assert result == {"A": False, "B": False}


# ── config gating: no endpoints configured → nothing warmed ──
@pytest.mark.asyncio
async def test_no_endpoints_configured(monkeypatch):
    _CountingOllama.calls = {}
    _config(monkeypatch, a="", b="")
    with patch.object(warmup, "OllamaProvider", _CountingOllama):
        result = await warmup.ensure_planning_endpoints_warm()
    assert result == {}
    assert _CountingOllama.calls == {}
