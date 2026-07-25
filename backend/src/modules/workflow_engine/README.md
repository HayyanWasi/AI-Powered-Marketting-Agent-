# Workflow Engine Module

Deterministic workflow orchestration using LangGraph.

## Structure

```
workflow_engine/
├── __init__.py              # Public surface: models + LangGraph classes
├── models.py                # WorkflowContext, WorkflowGraph, RetryPolicy, etc.
├── langgraph/
│   ├── __init__.py
│   ├── adapter.py           # Translates graphs to LangGraph StateGraph
│   └── executor.py          # Compiles and runs LangGraph apps
├── graphs/
│   ├── __init__.py
│   └── campaign_generation.py  # The single production pipeline
└── services/
    ├── retry_service.py     # Per-node retry tracking (used by tests)
    ├── resume_service.py    # Checkpoint save/resume (used by tests)
    ├── approval_service.py  # Human approval flow (used by tests)
    └── state_manager.py     # State tracking (used by tests)
```

## How it works

1. `campaign_generation.py` builds the LangGraph pipeline:
   - Instantiates all agents (strategy, content, asset, etc.)
   - Wraps each agent in a node with **built-in retry** (Constitution VI)
   - Compiles the graph with LangGraph `StateGraph` + `MemorySaver`
   - Registers on `LangGraphExecutor`

2. `orchestrator.py` (in `src/agents/`) is a thin facade that calls the executor

3. Retry logic lives INSIDE the node wrappers — callers never implement retry

## Key files

| File | Purpose |
|------|---------|
| `models.py` | All data models (frozen dataclasses) |
| `langgraph/adapter.py` | `LangGraphAdapter.build_state_graph()` |
| `langgraph/executor.py` | `LangGraphExecutor.execute()`, `.resume()` |
| `graphs/campaign_generation.py` | `build_executor()`, `compile_graph()`, node wrappers |
