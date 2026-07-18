# Quickstart: Workflow Engine Module

**Date**: 2026-07-18 | **Branch**: 012-workflow-engine

---

## Prerequisites

- Python 3.13+
- `uv` package manager
- Existing project dependencies: FastAPI, Pydantic v2

## Installation

```bash
uv add langgraph langgraph-checkpoint
```

## Basic Usage

### 1. Define Workflow Nodes

```python
from modules.workflow_engine.models import WorkflowContext, WorkflowNode
from modules.workflow_engine.models.retry_policy import RetryPolicy

async def step_one(context: WorkflowContext) -> WorkflowContext:
    output = {"step_one_result": "processed"}
    return context.with_updates(node_outputs=output)

async def step_two(context: WorkflowContext) -> WorkflowContext:
    output = {"step_two_result": context.node_outputs["step_one_result"]}
    return context.with_updates(node_outputs=output)

node_a = WorkflowNode(
    name="step_one",
    handler=step_one,
    retry_policy=RetryPolicy(max_retries=3, delay_seconds=1.0),
)

node_b = WorkflowNode(
    name="step_two", 
    handler=step_two,
)
```

### 2. Build a Workflow Graph

```python
from modules.workflow_engine.models import WorkflowGraph, GraphEdge

graph = WorkflowGraph(
    graph_id="my-workflow",
    nodes={"step_one": node_a, "step_two": node_b},
    entry_point="step_one",
    edges=[GraphEdge(source="step_one", target="step_two")],
    terminal_nodes={"step_two"},
)
```

### 3. Execute the Workflow

```python
from modules.workflow_engine.services import WorkflowEngineService

engine = WorkflowEngineService()
context = WorkflowContext.create(workflow_id="wf-001")

result = await engine.execute_workflow(graph, context)
print(f"Status: {result.status}")
print(f"Outputs: {result.final_context.node_outputs}")
```

### 4. Human Approval Workflow

```python
async def approval_node(context: WorkflowContext) -> WorkflowContext:
    from langgraph.types import interrupt
    from langgraph.prebuilt.interrupt import HumanInterrupt
    
    request = HumanInterrupt(
        action_request={"action": "approve_content", "args": context.node_outputs},
        description="Please review the generated content before publishing",
    )
    response = interrupt([request])
    return context.with_updates(approval_response=response[0])

# Approve via API:
# POST /api/v1/workflow/{thread_id}/approve
```

### 5. Resume from Checkpoint

```python
# After interruption or pause:
result = await engine.resume_workflow(thread_id="thread-001")
```

## Next Steps

- Read `data-model.md` for full entity reference
- Read `contracts/` for interface contracts
- Read `spec.md` for complete feature specification
- Run `uv run pytest tests/unit/workflow_engine/` to verify setup
