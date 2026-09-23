"""One-time warm-up of the planning-only Ollama endpoints.

The two Kaggle qwen3:8b GPUs load the model lazily on the first heavy request.
A cold first request can exceed the Cloudflare quick-tunnel response window and
fall back to a remote provider, even though the endpoint is healthy moments
later. A tiny warm-up call forces the model resident (Kaggle runs KEEP_ALIVE=-1,
so it stays resident) before real specialist generation.

Scope: PLANNING_OLLAMA_A / PLANNING_OLLAMA_B only. The global Ollama endpoint,
intake, and video are untouched.
"""

from __future__ import annotations

import asyncio
import logging
import time

from src.config.settings import settings
from src.services.llm_service import OllamaProvider, _remote_mode

logger = logging.getLogger(__name__)

# Tiny deterministic prompt: proves the model itself generates, not just that
# /v1/models responds. Output is bounded to a handful of tokens and discarded.
_WARM_PROMPT = "Reply with OK only."
_WARM_MAX_TOKENS = 8
# Cold model load on a Kaggle GPU can take a while; generous but bounded, and
# only paid once at warm-up rather than on a real specialist call.
_WARM_TIMEOUT_SECONDS = 120.0

# Endpoints proven warm this process (keyed by base URL). Never marked on
# failure, so a failed endpoint is retried on the next planning run — and a
# recreated endpoint (new URL, or cleared here) warms again safely.
_warmed: set[str] = set()
_locks: dict[str, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()


def is_warm(base_url: str) -> bool:
    """True when this endpoint has completed a successful warm-up this process."""
    return base_url.strip() in _warmed


def reset() -> None:
    """Forget all warm state (an endpoint may then warm again). Test/support use."""
    _warmed.clear()


async def _lock_for(key: str) -> asyncio.Lock:
    async with _locks_guard:
        return _locks.setdefault(key, asyncio.Lock())


async def _warm_one(label: str, base_url: str, model: str) -> bool:
    """Warm a single endpoint. Idempotent and safe under concurrency.

    A per-endpoint lock ensures concurrent callers cannot trigger duplicate
    warm-ups: the first warms, the rest observe the warmed state and return.
    """
    key = base_url.strip()
    if not key:
        return False

    lock = await _lock_for(key)
    async with lock:
        if key in _warmed:
            return True

        provider = OllamaProvider(base_url=key, model=model)
        start = time.perf_counter()
        try:
            await asyncio.to_thread(
                provider.generate,
                "",
                _WARM_PROMPT,
                _WARM_MAX_TOKENS,
                False,
                _WARM_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001 — any provider error means "not warm"
            logger.warning(
                "Planning Ollama %s warm-up: failure duration=%.1fs (%s)",
                label,
                time.perf_counter() - start,
                type(exc).__name__,
            )
            return False

        _warmed.add(key)
        logger.info(
            "Planning Ollama %s warm-up: success duration=%.1fs",
            label,
            time.perf_counter() - start,
        )
        return True


async def ensure_planning_endpoints_warm() -> dict[str, bool]:
    """Warm both configured planning endpoints once, concurrently.

    A and B are independent GPUs, so warming them at the same time does not
    violate the one-request-per-GPU rule. Never raises: a warm-up failure is
    logged and the endpoint is left not-ready, letting planning proceed on the
    existing remote fallback path. Returns {label: warmed?} for configured
    endpoints only.
    """
    if _remote_mode():
        # Remote-only mode never uses the planning Ollama GPUs, so it must not
        # contact them or block startup on their health. No-op skip.
        logger.info("Planning Ollama warm-up skipped (LLM_MODE=%s).", settings.llm_mode)
        return {}

    plans: list[tuple[str, str, str]] = []
    if settings.planning_ollama_a_base_url.strip():
        plans.append(
            ("A", settings.planning_ollama_a_base_url, settings.planning_ollama_a_model)
        )
    if settings.planning_ollama_b_base_url.strip():
        plans.append(
            ("B", settings.planning_ollama_b_base_url, settings.planning_ollama_b_model)
        )
    if not plans:
        return {}

    results = await asyncio.gather(
        *(_warm_one(label, url, model) for label, url, model in plans)
    )
    return {label: warmed for (label, _, _), warmed in zip(plans, results, strict=True)}
