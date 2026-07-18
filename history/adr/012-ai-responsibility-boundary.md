# ADR-012: AI Responsibility Boundary — Reasoning Only

**Status:** Accepted
**Date:** 2026-07-16

## Context

Early agent designs had AI agents performing workflow control, database access, state management, and business rule enforcement. Problems:
- Non-deterministic behavior in critical paths
- Hard to test and debug
- AI making business decisions (e.g., "is this profile complete?")
- Security risk (AI with DB access)
- Cost: LLM calls for deterministic logic

## Decision

**Strict separation of concerns:**

| AI Responsible For | Software (Deterministic) Responsible For |
|--------------------|------------------------------------------|
| Reasoning | Workflow control (routing, state machine) |
| Planning | Business rules (validation, uniqueness) |
| Writing (copy) | Database access (CRUD) |
| Image prompting | State management (checkpoints, history) |
| | Authentication/authorization |
| | API contracts, serialization |
| | Retry, timeout, circuit breaker |
| | Cost guardrails, rate limiting |

**Enforcement:**
- AI components are pure functions: `input → output` (no side effects)
- All I/O, state, control flow in workflow layer
- Business rules in validation services (deterministic code)
- AI never calls database, API, or file system directly

## Consequences

**Positive:**
- Deterministic system behavior
- Testable: AI components unit-testable with fixtures
- Secure: AI has no data access
- Cost control: No LLM calls for deterministic logic
- Debuggable: Clear boundary for observability

**Negative:**
- More code in workflow layer
- Must serialize complex context for AI calls
- Prompt engineering includes "you are a reasoning engine, do not..."

## Alternatives Considered

1. **AI agents with tools (function calling)**
   - Rejected: Non-deterministic tool selection; hard to debug

2. **Hybrid: AI decides next step, software executes**
   - Rejected: Still puts control flow in AI

3. **Full AI autonomy with guardrails**
   - Rejected: Too risky for production campaign system

## References

- Architecture Evolution Summary: "AI Responsibilities"
- ADR-006: LangGraph (workflow control is software)
- ADR-005: Structured JSON Communication (AI I/O contract)
- Plan.md: Architecture principles