# ADR-007: Modular Architecture with Separated Concerns

**Status:** Accepted
**Date:** 2026-07-16

## Context

The initial architecture had a single "AI module" containing all AI-related functionality. As the system grew, this became a monolith with:
- Mixed concerns (campaign CRUD, AI generation, workflow, observability)
- Tight coupling between business logic and AI implementation
- Difficult testing (AI and business logic intertwined)
- Hard to swap AI providers or prompts
- No clear ownership boundaries

## Decision

Decompose into **four independent modules** with clear boundaries:

| Module | Responsibilities |
|--------|------------------|
| **Campaign Management** | Campaign CRUD, configuration, goals, platforms, audience, history, status, publishing |
| **AI Generation** | Context Builder, Planning, Copy Generation, Image Prompt Generation, Image Generation, Validation |
| **Workflow** | LangGraph orchestration, routing, state, retry, resume, human approval, checkpoints |
| **Operations** | Logging, tracing, metrics, guardrails, prompt versioning, model versioning, cost tracking, history |

**Communication:** Modules communicate only through structured contracts (ADR-005). No direct imports across module boundaries.

## Consequences

**Positive:**
- Single responsibility per module
- Independent deployability (future)
- Clear ownership (teams can own modules)
- AI Generation swappable without touching Campaign Management
- Workflow engine swappable without touching AI Generation
- Operations is cross-cutting, not embedded
- Easier testing (mock at module boundaries)

**Negative:**
- More modules to manage
- Contract maintenance overhead
- Potential for distributed monolith if contracts are too chatty
- Initial decomposition effort

## Alternatives Considered

1. **Single AI module** (original)
   - Rejected: Violates SRP; coupling business logic to AI implementation

2. **Two modules: Business + AI**
   - Rejected: Workflow and Operations are distinct concerns

3. **Microservices from start**
   - Rejected: Premature; modules in-process first, extract later if needed

## References

- Architecture Evolution Summary: "Module Architecture"
- Plan.md: Technical Context, Architecture
- AGENTS.md: Project Structure