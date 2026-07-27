# Implementation Plan: Workflow Engine Module

**Branch**: `012-workflow-engine` | **Date**: 2026-07-18 | **Spec**: `/specs/012-workflow-engine/spec.md`

**Input**: Feature specification from `/specs/012-workflow-engine/spec.md`

---

# Summary

The Workflow Engine module provides deterministic workflow orchestration using LangGraph. It coordinates execution of registered workflow nodes through graph-based routing while remaining complestely independent of business logic, AI generation, campaign management, and persistence. The engine manages execution state, routing, retries, checkpoints, resume capability, human approval, and execution control through a stable public interface.

---

# Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**:
- LangGraph
- LangChain Core
- FastAPI
- Pydantic v2
- httpx

**Storage**:
- Stateless execution
- In-memory checkpoint management during workflow execution only
- No business data persistence

**Testing**:
- pytest
- pytest-asyncio
- unittest.mock

**Target Platform**:
Backend API Service

**Project Type**:
Single FastAPI backend module

**Performance Goals**:
- Workflow startup <200ms
- Deterministic graph execution
- Resume from checkpoint without re-executing completed nodes

**Constraints**:
- Completely independent from AI Generation Engine
- Completely independent from Campaign Management
- No business logic
- Graph-driven execution only
- Registered nodes only
- Deterministic execution
- Module remains stateless.
- Execution state exists only for the lifetime of a workflow execution.
- No business data persistence.

**Scale / Scope**:
- Multiple concurrent workflow executions
- Support sequential and conditional workflow execution through graph-defined routing.
- Human-in-the-loop workflows
- Checkpoint and resume support

---

# Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Test-First**: Tests written before implementation? (Principle I)
- [x] **Clean Code**: Type hints, dataclasses, docstrings, no print statements? (Principle II)
- [x] **KISS/DRY**: No unnecessary abstractions or duplicated orchestration logic? (Principle III)
- [x] **Fail Gracefully**: Structured error handling for node failures and checkpoint recovery? (Principle IV)
- [x] **Architecture**: Workflow orchestration separated from AI generation and campaign logic? (Principle V)
- [x] **Coverage**: ≥80% code coverage target? (Principle VI)
- [x] **Stack**: Uses approved technology stack including LangGraph? (Principle VII)

---

# Project Structure

## Documentation

```text
specs/012-workflow-engine/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

---

## Source Code

```text
backend/
src/
├── modules/
│   ├── workflow_engine/
│   │   ├── interfaces/
│   │   │   ├── workflow_engine.py
│   │   │
│   │   │
│   │   │
│   │   │
│   │   │
│   │   │
│   │   ├── services/
│   │   │   ├── workflow_engine_service.py
│   │   │   ├── graph_service.py
│   │   │   ├── routing_service.py
│   │   │   ├── retry_service.py
│   │   │   ├── resume_service.py
│   │   │   ├── checkpoint_service.py
│   │   │   ├── approval_service.py
│   │   │   ├── execution_service.py
|   |   |   ├── graph_builder.py
|   |   |   ├── checkpoint_manager.py
|   |   |   ├── approval_manager.py
|   |   |   ├── execution_controller.py
|   |   |   ├──node_registry.py
│   │   │   └──state_manager.py
│   │   ├── graph/
│   │   │   ├── graph_builder.py.py
│   │   │   ├── routing.py
│   │   │   ├── conditions.py
│   │   │   └── graph_compiler.py
│   │   │
│   │   ├── models/
│   │   │   ├── workflow_context.py
│   │   │   ├── workflow_graph.py
│   │   │   ├── workflow_node.py
│   │   │   ├── checkpoint.py
│   │   │   ├── workflow_state.py.py
│   │   │   ├── approval_request.py
│   │   │   └── retry_policy.py
│   │   │
│   │   ├── langgraph/
│   │   │   ├── adapter.py
│   │   │   ├── executor.py
│   │   │   └── registry.py
│   │   │
│   │   └── __init__.py
│   │
│   └── api/
│       └── routes/
│           └── workflow_engine.py
│
└── tests/
    ├── unit/
    │   └── workflow_engine/
    │       ├── test_graph_builder.py
    │       ├── test_routing.py
    │       ├── test_retry.py
    │       ├── test_checkpoint.py
    │       ├── test_resume.py
    │       ├── test_approval.py
    │       ├── test_execution.py
    │       └── test_registry.py
    │
    └── integration/
        ├── test_full_workflow.py
        ├── test_checkpoint_resume.py
        ├── test_parallel_execution.py
        └── test_human_approval.py
```

---

**Structure Decision**

The Workflow Engine is implemented as an independent backend module using LangGraph. It exposes only a public `WorkflowEngine` interface while encapsulating graph construction, routing, retries, checkpointing, approval handling, and execution control. Business modules interact only through this public interface.

---

# Complexity Tracking

No constitution violations identified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| None | N/A | N/A |

---

# Constitution Check (Post-Design)

*GATE: Must pass after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] Test-First Development
- [x] Clean Code Standards
- [x] KISS & DRY
- [x] Fail Gracefully
- [x] Architecture Separation
- [x] ≥80% Test Coverage
- [x] Approved Technology Stack

---

# Implementation Strategy

## Phase 0 – Research

- Evaluate LangGraph execution model
- Define workflow execution architecture
- Document checkpoint strategy
- Define retry behavior
- Define human approval lifecycle

---

## Phase 1 – Design

- WorkflowContext model
- WorkflowGraph model
- WorkflowNode contract
- RetryPolicy model
- Checkpoint model
- Public WorkflowEngine interface

---

## Phase 2 – Implementation

1. Build graph definition layer
2. Implement node registry
3. Implement routing engine
4. Implement state manager
5. Implement execution controller
6. Implement retry manager
7. Implement checkpoint manager
8. Implement resume engine
9. Implement approval manager
10. Integrate LangGraph executor
11. Expose WorkflowEngine API
---

## Phase 3 – Validation

- Unit testing
- Integration testing
- Retry testing
- Checkpoint recovery testing
- Parallel execution testing
- Human approval testing
- Performance validation
- Architecture verification
