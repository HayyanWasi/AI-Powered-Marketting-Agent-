"""Ambient execution trace context.

Carries the active workflow's trace_id/workflow_id so LLM services can attach
telemetry to the right trace without threading it through agent signatures.
"""

from contextvars import ContextVar, Token
from uuid import UUID

_execution_context: ContextVar[tuple[UUID, str] | None] = ContextVar(
    "operations_execution_context", default=None
)


def set_execution_context(trace_id: UUID, workflow_id: str) -> Token:
    """Bind the active trace to the current context. Returns a reset token."""
    return _execution_context.set((trace_id, workflow_id))


def get_execution_context() -> tuple[UUID, str] | None:
    """Return (trace_id, workflow_id) for the active workflow, or None."""
    return _execution_context.get()


def reset_execution_context(token: Token) -> None:
    """Restore the context to its state before the matching set call."""
    _execution_context.reset(token)
