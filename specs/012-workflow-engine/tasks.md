---
description: "Task breakdown for Workflow Engine Module implementation"
---

# Tasks: 012-workflow-engine

**Input**: Design documents from `/specs/012-workflow-engine/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `backend/src/modules/workflow_engine/`
- **Tests**: `backend/tests/unit/workflow_engine/`, `backend/tests/integration/`
- **API routes**: `backend/src/api/routes/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and module structure

- [ ] T001 Create workflow_engine module directory at `backend/src/modules/workflow_engine/` with subdirectories: interfaces/, services/, models/, langgraph/, graph/
- [ ] T002 [P] Create package initialization in `backend/src/modules/workflow_engine/__init__.py` with public exports
- [ ] T003 [P] Install and configure LangGraph + langchain-core dependencies; verify imports compile
- [ ] T004 [P] Create test directory structure at `backend/tests/unit/workflow_engine/` and `backend/tests/integration/` with `__init__.py` files

**Checkpoint**: Module structure ready — foundational development can begin

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and interfaces that MUST be complete before any user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 [P] Create WorkflowContext model in `backend/src/modules/workflow_engine/models/workflow_context.py` (immutable frozen dataclass with workflow_id, thread_id, state, node_outputs, errors, metadata, current_node; factory method `create()` and `with_updates()`)
- [ ] T006 [P] Create WorkflowGraph model in `backend/src/modules/workflow_engine/models/workflow_graph.py` (graph_id, nodes dict, entry_point, edges list, conditional_edges list, terminal_nodes set; validation for node references and cycle detection)
- [ ] T007 [P] Create WorkflowNode model in `backend/src/modules/workflow_engine/models/workflow_node.py` (name, description, handler callable, retry_policy, timeout_seconds, requires_approval)
- [ ] T008 [P] Create WorkflowState enum in `backend/src/modules/workflow_engine/models/workflow_state.py` (PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED)
- [ ] T009 [P] Create RetryPolicy model in `backend/src/modules/workflow_engine/models/retry_policy.py` (max_retries, delay_seconds, backoff_multiplier, max_delay_seconds)
- [ ] T010 [P] Create ExecutionCheckpoint model in `backend/src/modules/workflow_engine/models/checkpoint.py` (thread_id, checkpoint_id, timestamp, node_name)
- [ ] T011 [P] Create ApprovalRequest model in `backend/src/modules/workflow_engine/models/approval_request.py` (thread_id, node_name, request_data, status, rejection_reason, created_at, resolved_at)
- [ ] T012 [P] Create public WorkflowEngine interface in `backend/src/modules/workflow_engine/interfaces/workflow_engine.py` (abstract base with execute_workflow, resume_workflow, get_workflow_status, cancel_workflow, approve_workflow, reject_workflow)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Execute Complete Workflow Graph (Priority: P1) 🎯 MVP

**Goal**: Users can execute a complete workflow graph from entry node through all reachable terminal nodes, maintaining checkpoint state throughout execution.

**Independent Test**: Provide a workflow graph with 3 sequential nodes (A→B→C); execute and verify all nodes run in order, final WorkflowContext contains all outputs, and checkpoints exist after each node.

### Tests for US1 (TDD — write first, expect failure)

- [ ] T013 [P] [US1] Unit test graph builder in `backend/tests/unit/workflow_engine/test_graph_builder.py` (verify graph construction, node registration, edge validation)
- [ ] T014 [P] [US1] Unit test execution controller in `backend/tests/unit/workflow_engine/test_execution.py` (verify sequential execution, state transitions, error propagation)
- [ ] T015 [US1] Integration test complete workflow execution in `backend/tests/integration/test_full_workflow.py` (3-node sequential graph, verify all outputs and checkpoints)

### Implementation for US1

- [ ] T016 [P] [US1] Implement graph builder service in `backend/src/modules/workflow_engine/services/graph_builder.py` (constructs internal graph representation from WorkflowGraph model, validates nodes and edges)
- [ ] T017 [P] [US1] Implement node registry in `backend/src/modules/workflow_engine/services/node_registry.py` (stores registered node handlers, provides lookup by name)
- [ ] T018 [US1] Implement routing service in `backend/src/modules/workflow_engine/services/routing_service.py` (determines next node based on graph edges, handles conditional routing)
- [ ] T019 [US1] Implement state manager in `backend/src/modules/workflow_engine/services/state_manager.py` (initialize workflow state, update state transitions, store node outputs, track completed nodes, restore checkpoints)
- [ ] T020 [US1] Implement execution controller in `backend/src/modules/workflow_engine/services/execution_service.py` (orchestrates sequential node execution, manages state transitions, handles completion detection)
- [ ] T021 [US1] Implement WorkflowEngine service in `backend/src/modules/workflow_engine/services/workflow_engine_service.py` (coordinates complete workflow execution through the public interface, wires graph builder + registry + routing + state + execution together)

**Checkpoint**: User Story 1 should be fully functional and independently testable — MVP candidate

---

## Phase 4: User Story 2 — Node Retry and Error Recovery (Priority: P1)

**Goal**: Failed nodes are retried according to per-node retry policy without re-executing previously successful nodes.

**Independent Test**: Configure a node with max_retries=3; make it fail twice then succeed; verify exactly 3 attempts, only the failed node retried, and previously complete nodes retain their state.

### Tests for US2 (TDD — write first, expect failure)

- [ ] T022 [P] [US2] Unit test retry policy in `backend/tests/unit/workflow_engine/test_retry.py` (verify retry count logic, delay calculation, backoff, max retries exhaustion)
- [ ] T023 [US2] Integration test retry execution in `backend/tests/integration/test_retry_recovery.py` (node fails → retries → succeeds; node fails → retries exhausted → returns failure)

### Implementation for US2

- [ ] T024 [P] [US2] Implement retry service in `backend/src/modules/workflow_engine/services/retry_service.py` (evaluates per-node RetryPolicy, tracks attempt count, calculates delays with backoff, signals when retries exhausted)
- [ ] T025 [US2] Preserve completed node state during retries — verify in `backend/src/modules/workflow_engine/services/workflow_engine_service.py` that previous successful nodes are never re-executed during retry of a failed node (leverages LangGraph pending-writes mechanism)

**Checkpoint**: User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 — Checkpoint and Resume Capability (Priority: P1)

**Goal**: Workflow execution can be interrupted at any point and resumed from the last successful checkpoint without re-executing completed work.

**Independent Test**: Execute a 5-node workflow, interrupt after node 3, resume; verify nodes 1-3 are NOT re-executed and nodes 4-5 complete successfully with correct output state.

### Tests for US3 (TDD — write first, expect failure)

- [ ] T026 [P] [US3] Unit test checkpoint creation in `backend/tests/unit/workflow_engine/test_checkpoint.py` (verify checkpoint stored after each node, checkpoint contains correct state)
- [ ] T027 [P] [US3] Unit test resume logic in `backend/tests/unit/workflow_engine/test_resume.py` (verify resume restores state, skips completed nodes, starts from correct position)
- [ ] T028 [US3] Integration test resume workflow in `backend/tests/integration/test_checkpoint_resume.py` (interrupt 3/5 nodes, resume, verify remaining complete without re-execution)

### Implementation for US3

- [ ] T029 [P] [US3] Implement checkpoint service in `backend/src/modules/workflow_engine/services/checkpoint_service.py` (wraps LangGraph checkpointer; save/load/list checkpoints by thread_id; handles LangGraph InMemorySaver)
- [ ] T030 [US3] Implement resume service in `backend/src/modules/workflow_engine/services/resume_service.py` (resume execution from latest checkpoint for a given thread_id; restore WorkflowContext state; verify checkpoint integrity before resume)

**Checkpoint**: User Stories 1, 2, AND 3 should all work independently

---

## Phase 6: User Story 4 — Human Approval and Suspension (Priority: P2)

**Goal**: Workflow suspends at approval-required nodes for human review, then resumes on approval or returns rejection reason on rejection.

**Independent Test**: Execute workflow with an approval node; verify it pauses at the node; approve — verify it continues; execute again, reject — verify rejection reason returned and workflow suspended.

### Tests for US4 (TDD — write first, expect failure)

- [ ] T031 [P] [US4] Unit test approval request in `backend/tests/unit/workflow_engine/test_approval.py` (verify approval request creation, approve/reject transitions, status tracking)
- [ ] T032 [US4] Integration test approval suspend/resume in `backend/tests/integration/test_human_approval.py` (workflow pauses at approval node, approve → continues, reject → returns reason)

### Implementation for US4

- [ ] T033 [US4] Implement approval service in `backend/src/modules/workflow_engine/services/approval_service.py` (suspend workflow via LangGraph interrupt(), handle approve/resume, handle reject with reason, manage ApprovalRequest lifecycle)

**Checkpoint**: User Stories 1–4 all independently functional

---

## Phase 7: LangGraph Integration

**Purpose**: Wire all services into the LangGraph runtime for compilation and execution

- [ ] T034 [P] Configure LangGraph adapter in `backend/src/modules/workflow_engine/langgraph/adapter.py` (translates internal WorkflowNode/WorkflowGraph to LangGraph StateGraph nodes and edges)
- [ ] T035 [P] Configure graph compiler in `backend/src/modules/workflow_engine/langgraph/graph_compiler.py` (compiles StateGraph with checkpointer; validates graph structure; returns compiled app)
- [ ] T036 Configure executor in `backend/src/modules/workflow_engine/langgraph/executor.py` (invokes compiled graph; handles thread_id isolation; manages interrupt/resume lifecycle)
- [ ] T037 Register workflow nodes — connect registered node handlers into compiled graph via `backend/src/modules/workflow_engine/langgraph/registry.py`

**Checkpoint**: LangGraph runtime ready — external API can be connected

---

## Phase 8: API

**Purpose**: Expose Workflow Engine through REST API routes

- [ ] T038 [P] Create workflow API routes in `backend/src/api/routes/workflow.py` (POST /workflow/execute, POST /workflow/resume, POST /workflow/approve, POST /workflow/reject, GET /workflow/status)
- [ ] T039 Connect WorkflowEngine interface into API routes — inject WorkflowEngineService into route handlers via `backend/src/api/routes/workflow.py`

**Checkpoint**: Full API accessible and testable via HTTP

---

## Phase 9: Validation & Polish

**Purpose**: Cross-cutting validation, error handling, and performance

- [ ] T040 [P] Detect circular dependencies — implement graph validation in `backend/src/modules/workflow_engine/services/graph_builder.py` that rejects cycles before execution with structured CircuitDependencyError
- [ ] T041 [P] Detect invalid graph definitions — implement graph validation for missing entry point, orphan nodes, unreachable terminal nodes in `backend/src/modules/workflow_engine/services/graph_builder.py`
- [ ] T042 [P] Validate deterministic execution — add test in `backend/tests/integration/test_full_workflow.py` verifying same input → same output across multiple runs
- [ ] T043 [P] Validate checkpoint recovery — add test in `backend/tests/integration/test_checkpoint_resume.py` verifying successful nodes never re-executed on resume
- [ ] T044 [P] Validate execution status reporting — verify `get_workflow_status()` returns structured metadata (thread_id, state, current_node, completed_nodes, errors, checkpoint_id) in `backend/tests/unit/workflow_engine/test_execution.py`
- [ ] T045 [P] Performance validation — add benchmark tests for workflow startup <200ms, checkpoint resume speed, and deterministic execution consistency in `backend/tests/integration/test_performance.py`

**Checkpoint**: All validation passing

---

## Phase 10: Documentation

**Purpose**: Final documentation updates and architecture verification

- [ ] T046 [P] Update Quickstart at `specs/012-workflow-engine/quickstart.md` with final API usage examples and error handling patterns
- [ ] T047 [P] Update module documentation — verify all services and interfaces have docstrings; add module-level docs in `backend/src/modules/workflow_engine/__init__.py`
- [ ] T048 [P] Final architecture verification — confirm: no campaign logic, no AI generation logic, stateless execution (except checkpoints), public WorkflowEngine interface only, LangGraph isolated behind adapter

**Completion**: All phases complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3–6)**: All depend on Foundational completion
  - US1 → US2 → US3 → US4 (sequential — each builds on previous)
  - US4 can start after Phase 2 complete (parallel with US1–3 if staffing allows)
- **LangGraph Integration (Phase 7)**: Depends on all service implementations (US1–4)
- **API (Phase 8)**: Depends on LangGraph Integration
- **Validation (Phase 9)**: Depends on API — can run partially after each user story
- **Documentation (Phase 10)**: Depends on all prior phases

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Models before services
- Independent services can be parallel ([P] marker)
- Dependent services sequential
- Each story must be independently testable before advancing

### Parallel Opportunities (After Phase 2)

| Developer | Tasks |
|-----------|-------|
| Developer A | T016 graph_builder + T018 routing_service [US1] |
| Developer B | T017 node_registry + T019 state_manager [US1] |
| Developer C | T020 execution_service [US1] |
| Developer D | T022–T024 retry [US2] |
| Developer E | T026–T030 checkpoint + resume [US3] |

### Parallel Example: User Story 1

```bash
Task: "Unit test graph builder in tests/unit/workflow_engine/test_graph_builder.py"
Task: "Unit test execution controller in tests/unit/workflow_engine/test_execution.py"
Task: "Integration test complete workflow in tests/integration/test_full_workflow.py"
# Run tests first (expect failure), then implement:
Task: "Graph builder in services/graph_builder.py"
Task: "Node registry in services/node_registry.py"
Task: "Routing service in services/routing_service.py"
Task: "State manager in services/state_manager.py"
```

---

## Implementation Strategy

### MVP First (Phase 1–3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (models + interface)
3. Complete Phase 3: User Story 1 (graph execution)
4. **STOP and VALIDATE**: Test US1 independently
5. MVP ready — deploy/demo if needed

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (graph execution) → Test independently → MVP!
3. Add US2 (retry) → Test independently → Deploy
4. Add US3 (checkpoint/resume) → Test independently → Deploy
5. Add US4 (human approval) → Test independently → Deploy
6. Add LangGraph integration + API + validation → Final

### Parallel Team Strategy

With multiple developers:
1. Complete Setup + Foundational together (blocking)
2. Once foundational done:
   - Developer A: US1 services (graph_builder, routing, state, execution)
   - Developer B: US2 + US3 (retry, checkpoint, resume)
   - Developer C: US4 (approval) + API routes
3. Merge and integrate after each story

---

## Notes

- [P] tasks = different files, no dependencies on non-complete tasks
- [US*] label maps task to specific user story for traceability
- Each user story independently completable and testable
- Verify tests fail before implementing (TDD)
- Constitution check: module boundary isolation verified in T048
- Total tasks: 48
- Priority: US1 (P1), US2 (P1), US3 (P1), US4 (P2)
