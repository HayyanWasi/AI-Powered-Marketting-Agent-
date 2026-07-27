# ADR-001: Workflow-Centric Architecture over Agent-Centric

**Status:** Accepted
**Date:** 2026-07-16

## Context

Initial design modeled the system as multiple AI agents representing organizational departments (CMO, Audience Agent, SEO Agent, Hook Agent, CTA Agent, Brand Agent, etc.). Problems:
- Too many LLM calls (cost, latency)
- Agent responsibilities overlapped
- Difficult debugging (which agent decided what?)
- Complex maintenance (many prompt templates, agent configs)
- Non-deterministic orchestration

## Decision

**Architecture is workflow-centric, not agent-centric.** The system models the campaign lifecycle as a deterministic workflow:

```
Workflow
  ↓
Planning
  ↓
Generation
  ↓
Validation
  ↓
Human Review
```

AI components are specialized **workers** within this workflow, not autonomous agents. Orchestration, state, routing, and business rules remain in deterministic software (LangGraph).

## Consequences

**Positive:**
- 60-70% fewer LLM calls
- Lower cost, lower latency
- Deterministic execution flow
- Easier testing (workflow is testable state machine)
- Clear ownership: software = control, AI = reasoning

**Negative:**
- Less "agentic" flexibility (intentional)
- Workflow definition must anticipate paths
- Initial workflow design more upfront work

## Alternatives Considered

1. **Multi-agent with orchestrator agent** (e.g., LangGraph Supervisor)
   - Rejected: Still puts control flow in LLM

2. **Fully autonomous agents with tool use**
   - Rejected: Unpredictable, expensive, hard to debug

3. **Linear pipeline (no branching)**
   - Rejected: Need human review, regeneration, conditional paths

## References

- Architecture Evolution Summary: "Biggest Architectural Shift", "Overall Philosophy"
- Plan.md: Architecture, Workflow Graph
- AGENTS.md: Project Structure