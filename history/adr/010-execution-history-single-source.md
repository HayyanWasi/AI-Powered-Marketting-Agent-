# ADR-010: Execution History as Single Source of Truth

**Status:** Accepted
**Date:** 2026-07-16

## Context

No execution history existed originally. Campaign state was ephemeral. Problems:
- No audit trail
- Cannot debug past runs
- Cannot reproduce results
- No cost tracking per campaign
- Human review decisions lost

## Decision

**Every campaign execution persists a complete history record** containing:

| Artifact | Stored |
|----------|--------|
| Workflow state (at each checkpoint) | Yes |
| Generated strategy (planning output) | Yes |
| Generated caption (copy output) | Yes |
| Image prompt | Yes |
| Generated image (URL + metadata) | Yes |
| Validation results | Yes |
| User edits (with intent) | Yes |
| Human review decisions | Yes |
| Publish events | Yes |
| Token usage, cost, latency per node | Yes |
| Prompt version, model version | Yes |

**History is append-only.** Updates create new versions; previous versions retained.

**History ≠ Business Data.** Campaign entity (business data) and Execution History (operational data) are separate concerns. Campaign references latest execution; history retains all.

## Consequences

**Positive:**
- Full audit trail for compliance
- Reproducibility (re-run with same inputs)
- Cost attribution per campaign
- Debugging: exact state at failure
- Analytics: model performance, prompt effectiveness
- Human review accountability

**Negative:**
- Storage growth (mitigate: retention policy, compression)
- PII considerations in history
- Query complexity (history vs current state)

## Alternatives Considered

1. **No history** (original)
   - Rejected: Unacceptable for production

2. **Log aggregation only (ELK, Datadog)**
   - Rejected: Logs are unstructured; hard to query campaign-centric

3. **Event sourcing (full state reconstruction)**
   - Rejected: Overkill; current state + history snapshots sufficient

## References

- Architecture Evolution Summary: "History"
- ADR-009: Node-Level Resume (checkpoints feed history)
- ADR-011: Observability (consumes history)
- Plan.md: Campaign Model, History tracking