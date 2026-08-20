<!--
  Sync Impact Report
  ==================
  Version change: 1.0.0 → 2.0.0

  Modified principles:
    - III. KISS & DRY → III. Module-First Architecture
    - V. Architecture Constraints → V. Workflow-Driven Execution

  Added sections:
    - Module Ownership Rules
    - Workflow Architecture
    - Observability Standards
    - Recovery & Checkpoint Standards

  Removed sections:
    - Custom Python orchestration
    - Multi-agent architecture
    - Agent-specific testing requirements

  Templates requiring updates:
    - .specify/templates/plan-template.md: ⚠ Add Module Boundary Check
    - .specify/templates/spec-template.md: ⚠ Add Module Ownership section
    - .specify/templates/tasks-template.md: ⚠ Add Observability & Workflow tasks

  Follow-up TODOs:
    - Ratification date
-->

# AI Social Campaign Manager Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)

Every feature MUST begin with tests.

Production code MUST NOT be implemented until corresponding unit,
integration, or workflow tests exist.

Every public behavior introduced by a feature MUST be verifiable through
automated testing.

External APIs MUST always be mocked during testing.

---

### II. Clean Code & Type Safety

The project MUST use Python 3.13+.

All public functions MUST include:

- Type hints
- Google-style docstrings
- Explicit return types

Business logic MUST remain readable and deterministic.

Functions SHOULD perform one responsibility.

Logging MUST replace print statements.

Comments MUST explain *why*, never *what*.

---

### III. Module-First Architecture

The system is organized into independent business modules.

Each feature MUST belong to exactly one module.

A module owns:

- Business rules
- Models
- Validation
- Services
- Public interfaces

Modules MUST communicate only through their public interfaces.

Modules MUST NOT import another module's internal implementation.

Future features MUST extend existing modules or introduce new modules without
breaking existing module boundaries.

---

### IV. Separation of Responsibilities

Every module MUST have a single responsibility.

Current module ownership:

- Campaign Management
    - Campaign CRUD
    - Campaign configuration
    - Campaign lifecycle
    - Campaign publishing

- AI Generation Engine
    - Context Builder
    - Strategy Planner
    - Copy Generator
    - Image Prompt Editor
    - Image Generator
    - Content Validation
    - Intent Analyzer

- Workflow Engine
    - LangGraph orchestration
    - Retry strategy
    - Checkpoints
    - Human approval flow
    - State transitions

- Operations
    - Observability
    - Tracing
    - History
    - Metrics
    - Cost tracking
    - Monitoring

Responsibilities MUST NOT overlap.

---

### V. Workflow-Driven Execution

Workflow orchestration MUST be implemented using LangGraph.

LangGraph is responsible only for:

- execution order
- routing
- retries
- checkpoints
- resume
- state transitions

Business modules MUST remain executable without LangGraph.

The AI Generation module MUST NOT perform orchestration.

Workflow state MUST be recoverable from the latest successful checkpoint.

---

### VI. Reliability & Recovery

Every workflow MUST fail gracefully.

Failures MUST return user-friendly messages.

Failures MUST NOT expose internal implementation details.

Recoverable failures MUST resume from the latest checkpoint rather than restart
the entire workflow.

Retry logic belongs exclusively to the Workflow module.

Business modules MUST remain stateless whenever possible.

---

## Technical Stack & Architecture

### Backend

- Language: Python 3.13+
- Framework: FastAPI
- Testing: pytest
- Package Manager: uv
- Workflow Engine: LangGraph

### Database & Storage

- Database: Supabase PostgreSQL
- Object Storage: Supabase Storage
- Session Cache: In-memory cache (V1)

### AI

- LLM Provider: Gemini or OpenAI
- Image Generation: Cloudflare Workers AI (primary — img2img with reference / FLUX text2img) with Pollinations AI fallback
- Search: DuckDuckGo Search

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

---

## Project Architecture

```
Campaign Management
        │
        ▼
Workflow Engine (LangGraph)
        │
        ▼
AI Generation Engine
        │
        ▼
Operations
```

### Module Boundaries

Campaign Management owns:

- campaign data
- campaign lifecycle
- publishing

Workflow Engine owns:

- orchestration
- retries
- checkpoints
- approvals

AI Generation Engine owns:

- reasoning
- planning
- copywriting
- image generation
- validation

Operations owns:

- history
- tracing
- observability
- analytics
- monitoring

Modules MUST remain independent.

---

## Testing Standards

Required test categories:

- Unit Tests
- Integration Tests
- Workflow Tests
- API Tests

Every module MUST be tested independently.

Workflow tests MUST verify:

- checkpoint recovery
- retry behavior
- approval flow
- state transitions

External APIs MUST always be mocked.

Minimum backend coverage:

- Business Logic ≥80%

---

## Observability Standards

Every workflow execution MUST produce traceable metadata.

Observability MUST capture:

- execution status
- latency
- token usage
- cost
- errors
- workflow checkpoints

Business modules MUST NOT implement observability directly.

Observability belongs exclusively to the Operations module.

---

## Documentation Standards

Every module MUST contain:

- Feature specification
- Technical plan
- Task breakdown

Every architectural decision affecting multiple modules MUST include an ADR.

Prompt documentation MUST exist for every reasoning component.

---

## Immutable Workflow Context

Every workflow execution MUST begin by creating an immutable GenerationContext that contains all business data required for execution. Workflow nodes MUST consume only this snapshot and MUST NOT re-read business data from persistent storage during the same execution. Updates to campaigns, company profiles, audiences, or other business data affect only future workflow executions.
---
## Code Review Requirements

Before merging:

- All tests pass
- Coverage requirements met
- Module boundaries respected
- No hardcoded secrets
- Public interfaces documented
- Observability preserved
- Workflow remains resumable

Code reviews MUST reject:

- Cross-module implementation imports
- Business logic inside workflow nodes
- Workflow logic inside AI modules
- Circular dependencies

---

## Performance Requirements

Target execution:

- Complete campaign generation ≤60 seconds
- Database operations ≤100ms
- Workflow recovery ≤5 seconds
- Validation before publishing is mandatory

---

## Quality Gates

Every release MUST satisfy:

1. Tests pass
2. Coverage ≥80%
3. Module boundaries preserved
4. Workflow checkpoint recovery verified
5. Human approval required before publishing
6. Generated content validated before delivery
7. Production observability enabled

---

## Governance

This constitution is the authoritative engineering standard for the project.

Every specification, implementation, review, and release MUST comply with this
constitution.

### Amendment Procedure

1. Every architectural change MUST document its rationale.
2. Constitutional changes require stakeholder approval.
3. Versioning follows semantic versioning:
   - MAJOR → Architectural principle changes
   - MINOR → New principles or sections
   - PATCH → Clarifications and wording improvements
4. Every feature plan MUST include a Constitution Check.
5. Violations MUST be resolved before implementation.

### Compliance Review

Every pull request MUST verify:

- Module ownership
- Workflow compliance
- Testing compliance
- Documentation updates
- Architecture consistency

**Version:** 2.0.0

**Ratified:** TODO(RATIFICATION_DATE)

**Last Amended:** 2026-07-16