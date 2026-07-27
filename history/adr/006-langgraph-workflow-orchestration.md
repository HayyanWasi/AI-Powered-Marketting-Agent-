# ADR-006: LangGraph Workflow Orchestration over Linear Python Orchestration

**Status:** Accepted
**Date:** 2026-07-16

## Context

The original orchestration was linear Python code: `step1(); step2(); step3();`. This worked for simple pipelines but couldn't handle:
- Conditional execution (skip validation if human review skipped)
- Human-in-the-loop approval gates
- Retry with exponential backoff
- Resume from failure point
- Parallel execution of independent steps
- Checkpointing for long-running workflows
- State persistence across restarts

## Decision

Adopt **LangGraph** as the workflow orchestration engine.

**Responsibilities delegated to LangGraph:**
- State management (workflow state = single source of truth)
- Routing (conditional edges based on state)
- Retry policies (per-node, configurable)
- Resumption (checkpoint-based)
- Human approval nodes (interrupt/resume)
- Parallel execution (fan-out/fan-in)

**Application retains:**
- Business logic in nodes
- AI worker implementations
- Database operations
- External API calls

## Consequences

**Positive:**
- Native support for all workflow patterns needed
- Battle-tested, production-ready (LangChain ecosystem)
- Visual debugging (LangGraph Studio)
- Built-in persistence (PostgreSQL, SQLite, etc.)
- First-class human-in-the-loop support
- Declarative graph definition = easier maintenance

**Negative:**
- Additional dependency (LangGraph)
- Learning curve for team
- Graph definition can become complex
- Vendor lock-in to LangChain ecosystem (mitigated: standard Python functions as nodes)

## Alternatives Considered

1. **Linear Python orchestration** (original)
   - Rejected: No native support for human review, retries, resumption

2. **Custom state machine**
   - Rejected: Reinventing workflow engine; LangGraph is mature

3. **Temporal / Cadence / Airflow**
   - Rejected: Overkill for in-process workflows; designed for distributed systems

4. **LangChain LCEL (LangChain Expression Language)**
   - Rejected: Good for chains, not for complex graphs with cycles/human-in-loop

## References

- Architecture Evolution Summary: "Workflow Orchestration"
- Plan.md: Dependency Sequence item 5 (Workflow Graph)
- Research.md: Research 3 (Campaign Workflow Automation)