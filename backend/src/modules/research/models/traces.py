"""Conversation traces model for pre-built explainability ("Why X?" engine)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ConversationTrace(BaseModel):
    """Pre-computed answer to common marketer "Why?" questions."""

    model_config = ConfigDict(frozen=True)

    question_pattern: str  # e.g., "Why LinkedIn?", "Why $25 CPL?"
    decision_summary: str
    evidence_quotes: tuple[str, ...] = ()
    source_urls: tuple[str, ...] = ()
    confidence_score: float = 4.0


class ConversationTraces(BaseModel):
    """Collection of conversation traces for a research session."""

    model_config = ConfigDict(frozen=True)

    traces: tuple[ConversationTrace, ...] = ()

    def find_matching_trace(self, user_query: str) -> ConversationTrace | None:
        """Simple pattern matcher for conversation queries."""
        query_lower = user_query.lower()
        for trace in self.traces:
            if any(term in query_lower for term in trace.question_pattern.lower().split()):
                return trace
        return None

    def to_dict(self) -> dict[str, Any]:
        return {"traces": [t.model_dump() for t in self.traces]}
