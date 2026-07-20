# Implementation: Workflow Engine Module

**Feature Branch**: `012-workflow-engine`
**Implementation Date**: 2026-07-18
**Status**: Complete (core architecture)

---

## What Was Built

The Workflow Engine is a **domain-agnostic orchestration layer** that executes workflow graphs using LangGraph. It knows nothing about campaigns, marketing, or AI generation — it only executes registered nodes in dependency order.

---

## Phase 1: Setup — Module Structure Created

**What was done:**
- Created `backend/src/modules/workflow_engine/` with subdirectories: `interfaces/`, `services/`, `models/`, `langgraph/`
- Created `__init__.py` with public exports (`WorkflowEngine` interface only)
- Verified LangGraph + langchain-core dependencies compile
- Created test directory `backend/tests/unit/workflow_engine/`

**Key decision:** The module exposes only ONE public interface — `WorkflowEngine`. Everything else is internal. This enforces the boundary rule: external modules never depend on LangGraph directly.

---

## Phase 2: Foundational — Core Models and Interface

**What was done:**

Built 8 core models that define the entire workflow vocabulary:

| Model | Purpose |
|-------|---------|
| `WorkflowContext` | Immutable execution state — each node receives it, returns a new one. Never mutated. |
| `WorkflowGraph` | Complete graph definition — nodes, edges, conditional edges, entry point, terminal nodes. Includes cycle detection via DFS. |
| `WorkflowNode` | Registered executable unit — name, handler callable, retry policy, timeout, approval requirement. |
| `RetryPolicy` | Per-node retry config — max retries, delay, backoff multiplier, max delay cap. |
| `ExecutionCheckpoint` | Serialized state after successful node execution — thread_id, checkpoint_id, timestamp, node_name. |
| `ApprovalRequest` | Human approval suspension — thread_id, node_name, request_data, status (pending/approved/rejected), rejection_reason. |
| `ExecutionState` | Enum: PENDING → RUNNING → PAUSED → COMPLETED / FAILED / CANCELLED |
| `WorkflowResult` / `WorkflowStatus` | Output models for execution results and status queries. |

**Built the public interface** (`WorkflowEngine` ABC) with 6 abstract methods:
- `execute_workflow(graph, context)` — Run full graph
- `resume_workflow(thread_id)` — Resume from checkpoint
- `get_workflow_status(thread_id)` — Query current state
- `cancel_workflow(thread_id)` — Stop execution
- `approve_workflow(thread_id)` — Human approves
- `reject_workflow(thread_id, reason)` — Human rejects

**Key decision:** WorkflowContext is **frozen dataclass** — truly immutable. Nodes return new instances via `with_updates()`. This ensures determinism and prevents side effects.

---

## Phase 3: User Story 1 — Execute Complete Workflow Graph

**What it does:** Given a workflow graph with nodes A→B→C, the engine executes all nodes in dependency order, maintaining state at each step.

**Services built:**

| Service | What It Does |
|---------|-------------|
| `GraphBuilder` | Constructs internal graph representation from WorkflowGraph model. Validates nodes and edges. |
| `NodeRegistry` | Stores registered node handlers. Provides lookup by name. Nodes registered at startup, never discovered dynamically. |
| `RoutingService` | Determines next node based on graph edges. Handles conditional routing. |
| `StateManager` | Initializes workflow state, tracks completed nodes, stores node outputs, restores checkpoints. |
| `ExecutionService` | Orchestrates sequential node execution. Manages state transitions. Detects completion (all terminal nodes reached). |
| `WorkflowExecution` | Main service — wires GraphBuilder + Registry + Routing + State + Execution together. Coordinates full workflow. |

**Key decision:** Execution is sequential with parallel potential for independent nodes. The engine walks the graph, executes each node, stores output in state, and moves to the next.

---

## Phase 4: User Story 2 — Node Retry and Error Recovery

**What it does:** When a node fails, only that node is retried — previously completed nodes are never re-executed.

**Service built:**

| Service | What It Does |
|---------|-------------|
| `RetryService` | Evaluates per-node RetryPolicy. Tracks attempt count. Calculates delays with exponential backoff. Signals when retries exhausted. |

**Key decision:** Retry applies ONLY to the failed node. The engine preserves completed node state via StateManager. This is the "never restart from beginning" guarantee.

---

## Phase 5: User Story 3 — Checkpoint and Resume

**What it does:** Workflow can be interrupted at any point and resumed from the last successful checkpoint without re-executing completed work.

**Services built:**

| Service | What It Does |
|---------|-------------|
| `CheckpointService` | Wraps LangGraph checkpointer. Save/load/list checkpoints by thread_id. |
| `ResumeService` | Resume execution from latest checkpoint. Restore WorkflowContext state. Verify checkpoint integrity. |

**Key decision:** Checkpoints are managed internally by LangGraph through InMemorySaver. The engine never exposes checkpoint storage details to external modules.

---

## Phase 6: User Story 4 — Human Approval and Suspension

**What it does:** Workflow suspends at approval-required nodes for human review. Resumes on approval. Returns rejection reason on rejection.

**Service built:**

| Service | What It Does |
|---------|-------------|
| `ApprovalService` | Manages ApprovalRequest lifecycle. Creates request → suspends workflow → handles approve/resume or reject with reason. |

**Key decision:** On rejection, the engine does NOT decide business actions. It returns the rejection reason and current state to the caller. The caller decides what happens next.

---

## Phase 7: LangGraph Integration

**What was done:** Wired all services into LangGraph runtime.

| Component | What It Does |
|-----------|-------------|
| `LangGraphAdapter` | Translates WorkflowNode/WorkflowGraph to LangGraph StateGraph nodes and edges. |
| `LangGraphExecutor` | Invokes compiled graph. Handles thread_id isolation. Manages interrupt/resume lifecycle. |
| `NodeRegistry` | Connects registered node handlers into compiled graph. |

**Key decision:** LangGraph is hidden behind adapters. External modules never depend on LangGraph directly. Future engine replacements don't change the public API.

---

## Phase 8: API — REST Endpoints

**5 endpoints exposed:**

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/workflow/execute` | Start workflow execution |
| POST | `/workflow/resume` | Resume paused workflow |
| POST | `/workflow/approve` | Approve human approval node |
| POST | `/workflow/reject` | Reject with reason |
| GET | `/workflow/status/{thread_id}` | Query execution status |

**Router registered in main.py.**

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Setup | T001-T004 | ✅ Complete |
| Phase 2: Foundational | T005-T012 | ✅ Complete |
| Phase 3: US1 — Execute Workflow | T013-T021 | ✅ Complete |
| Phase 4: US2 — Retry | T022-T025 | ✅ Complete |
| Phase 5: US3 — Checkpoint/Resume | T026-T030 | ✅ Complete |
| Phase 6: US4 — Human Approval | T031-T033 | ✅ Complete |
| Phase 7: LangGraph Integration | T034-T037 | ✅ Complete |
| Phase 8: API | T038-T039 | ✅ Complete |
| Phase 9: Validation | T040-T045 | ⚠️ Partial |
| Phase 10: Documentation | T046-T048 | ⚠️ Partial |

**Total**: 48 tasks — **42 completed, 6 partial**

---

## Test Results

```
28 passed (workflow engine unit tests)
290 passed (full unit test suite)
0 failures
```

---

## Bug Fixed

- `models.py:602` — `WorkflowStatus.__post_init__` had `self.completed_nodes + self.pending_nodes` (list concatenation instead of integer addition). Fixed to `len()`.

---

## Files Inventory

### Models (1 file, 600+ lines)
- `models.py` — All core data models

### Services (10 files)
- `graph_builder.py`, `node_registry.py`, `routing_service.py`
- `state_manager.py`, `execution_service.py`, `workflow_execution.py`
- `checkpoint_service.py`, `retry_service.py`, `resume_service.py`, `approval_service.py`

### LangGraph (3 files)
- `adapter.py`, `executor.py`, `registry.py`

### API (1 file)
- `routes/workflow.py` — 5 endpoints

### Tests (2 files, 28 tests)
- `test_models.py` — 17 model tests
- `test_services.py` — 11 service tests

---

*Generated from specs/012-workflow-engine/ task verification against actual source code.*
