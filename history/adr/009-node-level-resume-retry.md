# ADR-009: Node-Level Workflow Resume and Retry

**Status:** Accepted
**Date:** 2026-07-16

## Context

Original error handling: on any failure, restart entire workflow from beginning. Problems:
- Wasted compute (re-running successful nodes)
- High cost (re-paying for LLM calls, image generation)
- Poor reliability (transient failures cascade)
- No partial progress visibility

## Decision

**Resume from failed node:** LangGraph checkpoints state after each node. On failure:
1. Identify failed node
2. Load latest checkpoint before failed node
3. Retry failed node (with configurable retry policy: exponential backoff, max attempts)
4. Continue forward from there

**Completed steps are never re-executed** unless explicitly invalidated (see ADR-008).

**Retry policies per node type:**
- LLM calls: 3 retries, exponential backoff (transient API errors)
- Image generation: 2 retries (longer timeout)
- Validation: 1 retry (deterministic, unlikely transient)
- Human review: No retry (waits for input)

## Consequences

**Positive:**
- Significant cost savings on transient failures
- Faster recovery (skip completed work)
- Better observability (see exactly where failed)
- Enables human-in-the-loop at any point

**Negative:**
- Requires deterministic, idempotent nodes (or explicit idempotency keys)
- Checkpoint storage overhead
- Complexity in state serialization
- Must handle non-retryable errors (e.g., invalid input) differently

## Alternatives Considered

1. **Full restart** (original)
   - Rejected: Unacceptable for production

2. **External workflow engine (Temporal, Airflow)**
   - Rejected: Overkill; LangGraph checkpoints sufficient for in-process

3. **Manual checkpointing in application code**
   - Rejected: Reinventing LangGraph; error-prone

## References

- Architecture Evolution Summary: "Retry Strategy"
- ADR-006: LangGraph Workflow Orchestration (provides checkpointing)
- Plan.md: Dependency Sequence, Workflow Graph