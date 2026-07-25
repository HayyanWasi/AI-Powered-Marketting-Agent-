"""Workflow Engine Module

This module provides deterministic workflow orchestration using LangGraph.
It coordinates execution of registered workflow nodes through graph-based
routing while remaining completely independent of business logic, AI
generation, campaign management, and persistence.

Public surface:
    - models: WorkflowContext, WorkflowGraph, WorkflowNode, RetryPolicy,
      ApprovalRequest, ExecutionCheckpoint, ExecutionState, ApprovalStatus,
      ExecutionError, WorkflowResult, WorkflowStatus
    - langgraph.adapter: LangGraphAdapter — translates graphs to StateGraph
    - langgraph.executor: LangGraphExecutor — compiles and runs graphs
    - graphs.campaign_generation: the single production pipeline graph
"""

from .models import (
    WorkflowContext,
    WorkflowGraph,
    WorkflowNode,
    RetryPolicy,
    ApprovalRequest,
    ExecutionCheckpoint,
    ExecutionState,
    ApprovalStatus,
    ExecutionError,
    WorkflowResult,
    WorkflowStatus,
)
from .langgraph.adapter import LangGraphAdapter
from .langgraph.executor import LangGraphExecutor
from .graphs.campaign_generation import build_executor, GRAPH_ID

__all__ = [
    "WorkflowContext",
    "WorkflowGraph",
    "WorkflowNode",
    "RetryPolicy",
    "ApprovalRequest",
    "ExecutionCheckpoint",
    "ExecutionState",
    "ApprovalStatus",
    "ExecutionError",
    "WorkflowResult",
    "WorkflowStatus",
    "LangGraphAdapter",
    "LangGraphExecutor",
    "build_executor",
    "GRAPH_ID",
]
