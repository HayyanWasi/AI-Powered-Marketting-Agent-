# Research: Workflow Engine Module

**Date**: 2026-07-18 | **Branch**: 012-workflow-engine

---

## LangGraph Execution Model

### Decision

Use `StateGraph` with typed state (Pydantic-based `WorkflowContext`) as the core execution model. Nodes are registered via `add_node(name, callable)`, edges via `add_edge()` and `add_conditional_edges()`. Entry point via `add_edge(START, first_node)`.

### Rationale

LangGraph's `StateGraph` provides:
- **Deterministic execution**: given the same state and graph, execution is fully deterministic
- **Dependency-based ordering**: edges define which nodes depend on which, and nodes without dependencies execute in parallel automatically
- **Conditional routing**: `add_conditional_edges` enables data-dependent branching
- **Fan-in/fan-out**: lists of source nodes in `add_edge([A, B], C)` implement parallel-to-sequential transitions

### Alternatives Considered

- Custom Python orchestration (rejected: violates constitution Principle V requiring LangGraph)
- Simple DAG runner (rejected: no built-in checkpoint/resume/interrupt support)

---

## Checkpoint Strategy

### Decision

Use `InMemorySaver` (from `langgraph.checkpoint.memory`) as the default checkpoint implementation, with the `Checkpointer` interface exposed so the application can swap in `SqliteSaver` or custom implementations.

### Rationale

- `InMemorySaver` is the simplest checkpoint backend and requires no external database setup
- The `BaseCheckpointSaver` interface is standardized across all LangGraph checkpointers
- Checkpoint content is managed entirely by LangGraph — the engine never reads/writes checkpoint data directly
- Checkpoints are captured after each superstep (node execution) automatically via the compiled graph's checkpointer

### Alternatives Considered

- `SqliteSaver` (deferred: adds filesystem dependency; can be swapped in later via the interface)
- Custom checkpoint storage (rejected: violates "external modules never touch checkpoint internals" requirement)

---

## Retry Behavior

### Decision

Retry is implemented as **LangGraph conditional routing** within the graph, not as a framework-level retry decorator. Each node defines its retry policy (count, delay, strategy). When a node fails:
1. The node returns a failure state in the `WorkflowContext`
2. A conditional edge routes back to the node if retries remain, or to an error terminal if exhausted
3. Previously completed nodes are preserved via LangGraph's pending-writes mechanism

### Rationale

- LangGraph's `add_conditional_edges` naturally models retry as graph routing
- Failed nodes that modify state before failing are handled by the pending-writes mechanism — LangGraph only stores writes from *successful* nodes at each superstep
- Per-node retry policies are stored in the `WorkflowNode` configuration and evaluated by the routing function

### Alternatives Considered

- `tenacity` or `backoff` decorators on node functions (rejected: bypasses LangGraph state management, makes checkpoint/resume unreliable)
- Framework-level retry in executor (rejected: doesn't preserve LangGraph's per-superstep write semantics)

---

## Human Approval Lifecycle

### Decision

Use LangGraph's built-in `interrupt()` function to pause execution for human approval. The flow is:
1. A node calls `interrupt([HumanInterrupt])` with the approval request details
2. LangGraph raises `GraphInterrupt`, the executor stores the checkpoint, and returns control to the caller
3. The caller processes approval externally and resumes via `graph.invoke(None, config)` with the resume value
4. The interrupted node re-executes with the resume value available

### Rationale

- `interrupt()` is LangGraph's native human-in-the-loop mechanism — no custom suspension logic needed
- Checkpoint is automatically saved at the interrupt point
- Resume automatically restores state from the checkpoint
- The `HumanInterrupt`/`HumanResponse` types provide structured data for the approval UI/API

### Alternatives Considered

- Custom asyncio.Event-based suspension (rejected: no checkpoint integration, breaks resume)
- External database approval queue (rejected: couples engine to external storage, violates stateless principle)

---

## Graph Compilation and Execution

### Decision

Compile the `StateGraph` via `graph.compile(checkpointer=checkpointer)` at the point of execution. Each workflow execution uses a unique `thread_id` in the config for isolation.

### Rationale

- Thread isolation via `thread_id` enables multiple concurrent workflow executions without state collision
- Compilation validates the graph structure (missing nodes, orphan edges, cycles) upfront
- The checkpointer is injected at compile time, keeping the graph definition itself stateless

---

## Parallel Execution

### Decision

Parallel execution is implicit in LangGraph's edge model. Nodes without a dependency path between them execute concurrently. The fan-in pattern (`add_edge([A, B], C)`) waits for all predecessors before advancing.

### Rationale

- No extra configuration needed — LangGraph's task executor handles parallelism automatically
- Determinism is preserved because LangGraph processes all tasks at a given superstep before advancing
- The parallel execution behavior is driven entirely by the graph edge structure

---

## Public Interface Pattern

### Decision

The public `WorkflowEngine` interface is a thin adapter that wraps the compiled LangGraph graph. It exposes:
- `execute_workflow(graph_def, context)` → execute from start
- `resume_workflow(thread_id, resume_value)` → resume from checkpoint
- `get_status(thread_id)` → execution status
- `approve(thread_id)` / `reject(thread_id, reason)` → handle approval

All other components (graph building, routing, checkpoints) are internal.

### Rationale

- Single entry point pattern matches the `WorkflowEngine` interface requirement
- Encapsulates LangGraph internals from external consumers
- Other modules (campaign management, AI generation) depend only on this interface

---

## Dependency Summary

| Dependency | Version | Purpose |
|---|---|---|
| langgraph | ≥0.2.0 | Core graph execution engine |
| langgraph-checkpoint | included | Checkpoint saver interface |
| pydantic | ≥2.0 | WorkflowContext and model validation |
| FastAPI | (existing) | API routes for workflow control |
| httpx | (existing) | Async HTTP (if needed for inter-service) |

No new external dependencies beyond LangGraph are required.
