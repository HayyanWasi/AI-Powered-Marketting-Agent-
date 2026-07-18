# Data Model: Workflow Engine Module

**Date**: 2026-07-18 | **Branch**: 012-workflow-engine

---

## WorkflowContext

Immutable execution state shared across workflow nodes. Each node receives an immutable `WorkflowContext` and returns a new instance with its outputs. Existing context is never modified in place.

| Field | Type | Required | Description |
|---|---|---|---|
| `workflow_id` | `str` | Yes | Unique identifier for this workflow execution |
| `thread_id` | `str` | Yes | LangGraph thread ID for checkpoint isolation |
| `state` | `ExecutionState` | Yes | Current execution state enum |
| `node_outputs` | `Dict[str, Any]` | Yes | Accumulated outputs from completed nodes |
| `errors` | `List[ExecutionError]` | No | Errors encountered during execution |
| `metadata` | `Dict[str, Any]` | No | Optional execution metadata |
| `current_node` | `Optional[str]` | No | Name of the currently executing node |

### Validation Rules

- Must be created via `WorkflowContext.create()` factory (no direct construction)
- `workflow_id` must be non-empty
- `state` must be a valid `ExecutionState` value
- Once created, no field may be mutated — only replaced via `with_updates()`

### State Transitions

```
PENDING → RUNNING → PAUSED → RUNNING → COMPLETED
                   → RUNNING → FAILED
                   → RUNNING → CANCELLED
```

---

## WorkflowGraph

Complete workflow definition containing registered nodes, execution edges, routing rules, and entry points.

| Field | Type | Required | Description |
|---|---|---|---|
| `graph_id` | `str` | Yes | Unique identifier for this graph definition |
| `nodes` | `Dict[str, WorkflowNode]` | Yes | Map of node name to node definition |
| `entry_point` | `str` | Yes | Name of the first node to execute |
| `edges` | `List[GraphEdge]` | Yes | Directed edges between nodes |
| `conditional_edges` | `List[ConditionalEdge]` | No | Data-dependent routing rules |
| `terminal_nodes` | `Set[str]` | Yes | Set of terminal node names |

### Validation Rules

- `entry_point` must refer to a registered node in `nodes`
- All `edges` and `conditional_edges` source/target must refer to registered nodes
- `terminal_nodes` must be a subset of registered node names
- Graph must not contain cycles (validated by `GraphValidator` before execution)
- At least one terminal node must be reachable from entry point

---

## WorkflowNode

A registered executable unit that receives an immutable `WorkflowContext`, performs a single task, and returns a new immutable `WorkflowContext`.

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | Yes | Unique node name within the graph |
| `description` | `str` | No | Human-readable description of node purpose |
| `handler` | `Callable` | Yes | The executable function (registered at startup) |
| `retry_policy` | `RetryPolicy` | No | Retry configuration for this node |
| `timeout_seconds` | `Optional[float]` | No | Max execution time before timeout |
| `requires_approval` | `bool` | No | Whether node pauses for human approval |

### Handler Contract

```python
async def node_handler(context: WorkflowContext) -> WorkflowContext:
    """Process the workflow context and return updated context.
    
    Args:
        context: Immutable current workflow context.
        
    Returns:
        New WorkflowContext with node outputs added.
        
    Raises:
        WorkflowNodeError: On unrecoverable node failure.
    """
```

### Validation Rules

- `name` must be non-empty and unique within the graph
- `handler` must be a registered callable (not dynamically imported)
- `retry_policy.count` must be >= 0
- `retry_policy.delay_seconds` must be >= 0

---

## RetryPolicy

Per-node retry configuration.

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `max_retries` | `int` | Yes | 0 | Maximum retry attempts |
| `delay_seconds` | `float` | Yes | 1.0 | Delay between retries in seconds |
| `backoff_multiplier` | `float` | No | 1.0 | Multiplier for exponential backoff |
| `max_delay_seconds` | `Optional[float]` | No | None | Maximum delay cap |

---

## ExecutionCheckpoint

Serialized workflow state captured after successful node execution. Managed internally by LangGraph — the engine never reads/writes checkpoint data directly.

| Field | Type | Description |
|---|---|---|
| `thread_id` | `str` | LangGraph thread ID |
| `checkpoint_id` | `str` | Unique checkpoint identifier |
| `timestamp` | `datetime` | When checkpoint was created |
| `node_name` | `str` | Last successfully completed node |

Notable: The full checkpoint payload is managed by LangGraph's `Checkpointer`. The engine only tracks checkpoint metadata for status reporting.

---

## ApprovalRequest

Represents a workflow suspension awaiting human approval before execution may continue.

| Field | Type | Required | Description |
|---|---|---|---|
| `thread_id` | `str` | Yes | Workflow thread ID |
| `node_name` | `str` | Yes | Node requesting approval |
| `request_data` | `Dict[str, Any]` | Yes | Data presented to approver |
| `status` | `ApprovalStatus` | Yes | Current status (PENDING, APPROVED, REJECTED) |
| `rejection_reason` | `Optional[str]` | No | Reason if rejected |
| `created_at` | `datetime` | Yes | When request was created |
| `resolved_at` | `Optional[datetime]` | No | When request was resolved |

---

## ExecutionState

Enumeration of possible workflow execution states.

| Value | Description |
|---|---|
| `PENDING` | Workflow created but not started |
| `RUNNING` | Workflow actively executing |
| `PAUSED` | Workflow paused for human approval |
| `COMPLETED` | All reachable terminal nodes executed successfully |
| `FAILED` | Workflow terminated with unrecoverable error |
| `CANCELLED` | Workflow cancelled by caller |

---

## ExecutionError

Structured error record for workflow failures.

| Field | Type | Description |
|---|---|---|
| `node_name` | `str` | Node where error occurred |
| `error_code` | `str` | Machine-readable error code |
| `message` | `str` | Human-readable error message |
| `retry_count` | `int` | Number of retries attempted |
| `timestamp` | `datetime` | When error occurred |
| `recoverable` | `bool` | Whether error is recoverable via retry/resume |

---

## GraphEdge

A directed edge connecting two nodes.

| Field | Type | Description |
|---|---|---|
| `source` | `str` | Source node name |
| `target` | `str` | Target node name |

## ConditionalEdge

A data-dependent routing rule.

| Field | Type | Description |
|---|---|---|
| `source` | `str` | Source node name |
| `condition` | `Callable[[WorkflowContext], str]` | Function that returns target node name |
| `target_map` | `Dict[str, str]` | Map of condition output → target node |

---

## Relationships

```
WorkflowGraph
  ├── 1..* WorkflowNode (nodes map)
  ├── 0..* GraphEdge (edges list)
  ├── 0..* ConditionalEdge (conditional_edges list)
  └── 1 entry_point → WorkflowNode.name

WorkflowNode
  ├── 0..1 RetryPolicy (retry_policy)
  └── 1 handler (registered callable)

WorkflowContext
  ├── 1 ExecutionState (state)
  └── 0..* ExecutionError (errors list)

ExecutionCheckpoint
  └── 1 WorkflowContext (state snapshot, managed by LangGraph)

ApprovalRequest
  ├── 1 WorkflowContext (context at request time)
  └── 1 ApprovalStatus
```
