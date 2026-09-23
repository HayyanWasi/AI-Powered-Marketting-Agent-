"""LinkedIn-specific serialization for the single-GPU local Ollama endpoint.

Local Ollama (qwen3:8b) has an effective execution capacity of one. A single
LinkedIn generation request, however, issues several LLM calls at once: up to
three posts (the post-generation semaphore) plus the outreach sequence, run
together by the outer ``asyncio.gather`` in the LinkedIn route. Against a
single-GPU endpoint the queued calls exceed the HTTP timeout and the request
fails.

This module provides ONE shared gate used by every LinkedIn generator so that at
most one LinkedIn *local-Ollama* call is ever in flight. The invariant is:

    MAX ACTIVE LINKEDIN LOCAL OLLAMA CALLS = 1

Scope is deliberately narrow:

* It is LinkedIn-specific — planning, intake, and video never import it, so
  their Ollama/remote usage is untouched.
* It engages only when the call actually targets local Ollama, so LinkedIn runs
  on remote providers are never needlessly serialized.

The gate is created once per event loop. In production there is a single
long-lived loop, so a single ``Semaphore(1)`` serializes all LinkedIn
local-Ollama work; under pytest each test's loop gets its own gate, avoiding the
"bound to a different event loop" error that a module-global semaphore would hit.
"""

from __future__ import annotations

import asyncio
import threading
import weakref
from contextlib import asynccontextmanager
from typing import Any

# LinkedIn-only bounded timeout for a single local-Ollama generation. qwen3:8b
# can exceed the global 60s provider timeout on one isolated request; this longer
# bound is threaded through as a per-request timeout that the canonical service
# applies ONLY to the local-Ollama leg. Global/default, planning, intake, and
# video timeouts are unchanged.
LINKEDIN_LOCAL_OLLAMA_TIMEOUT_SECONDS = 120.0

# One Semaphore(1) per running event loop. WeakKeyDictionary lets closed loops
# (e.g. per-test loops) be garbage-collected without leaking.
_gates: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
    weakref.WeakKeyDictionary()
)
_gates_guard = threading.Lock()


def linkedin_local_ollama_gate() -> asyncio.Semaphore:
    """Return the shared LinkedIn local-Ollama permit for the current loop."""
    loop = asyncio.get_running_loop()
    with _gates_guard:
        gate = _gates.get(loop)
        if gate is None:
            gate = asyncio.Semaphore(1)
            _gates[loop] = gate
        return gate


def _targets_local_ollama(llm_router: Any) -> bool:
    """True when this router will execute against a local Ollama endpoint.

    The router wraps a canonical ``LLMService``; ``has_ollama_provider()`` is the
    truthful signal that an Ollama leg is present. Anything without that method
    (pure remote services, unexpected doubles) is treated as non-Ollama so the
    gate stays a no-op for them.
    """
    service = getattr(llm_router, "llm", None)
    checker = getattr(service, "has_ollama_provider", None)
    if not callable(checker):
        return False
    try:
        return bool(checker())
    except Exception:
        return False


@asynccontextmanager
async def linkedin_local_ollama_slot(llm_router: Any):
    """Hold the shared LinkedIn local-Ollama permit for the duration of a call.

    Acquires the single per-loop gate only when ``llm_router`` targets local
    Ollama; otherwise it is a no-op. The permit is always released, including on
    exception, so a failed generation never wedges the gate.
    """
    if _targets_local_ollama(llm_router):
        gate = linkedin_local_ollama_gate()
        async with gate:
            yield
    else:
        yield
