# Workflow Engine Public Interface

**Date**: 2026-07-18

## Overview

The `WorkflowEngine` is the single public entry point for the Workflow Engine module. All external modules (Campaign Management, AI Generation) interact exclusively through this interface.

---

## Interface Definition

```python
class WorkflowEngine(ABC):
    @abstractmethod
    async def execute_workflow(
        self,
        graph: WorkflowGraph,
        context: WorkflowContext,
    ) -> WorkflowResult:
        """Execute a workflow graph from start to completion.
        
        Args:
            graph: The workflow graph definition to execute.
            context: Initial workflow context with starting state.
            
        Returns:
            WorkflowResult containing final context and execution metadata.
            
        Raises:
            GraphValidationError: If the graph definition is invalid.
            WorkflowExecutionError: If execution encounters an unrecoverable error.
        """
    
    @abstractmethod
    async def resume_workflow(
        self,
        thread_id: str,
        resume_value: Optional[Any] = None,
    ) -> WorkflowResult:
        """Resume a paused or interrupted workflow from its last checkpoint.
        
        Args:
            thread_id: The thread ID of the workflow to resume.
            resume_value: Optional value to pass to the interrupted node.
            
        Returns:
            WorkflowResult containing final context and execution metadata.
            
        Raises:
            CheckpointNotFoundError: If no checkpoint exists for the thread.
            WorkflowExecutionError: If execution encounters an unrecoverable error.
        """
    
    @abstractmethod
    async def get_workflow_status(
        self,
        thread_id: str,
    ) -> WorkflowStatus:
        """Get the current execution status of a workflow.
        
        Args:
            thread_id: The thread ID of the workflow.
            
        Returns:
            WorkflowStatus containing state, progress, and metadata.
            
        Raises:
            WorkflowNotFoundError: If no workflow exists for the thread.
        """
    
    @abstractmethod
    async def cancel_workflow(
        self,
        thread_id: str,
    ) -> None:
        """Cancel a running or paused workflow.
        
        Args:
            thread_id: The thread ID of the workflow to cancel.
            
        Raises:
            WorkflowNotFoundError: If no workflow exists for the thread.
        """
    
    @abstractmethod
    async def approve_workflow(
        self,
        thread_id: str,
    ) -> WorkflowResult:
        """Approve a workflow paused for human approval.
        
        Args:
            thread_id: The thread ID of the workflow.
            
        Returns:
            WorkflowResult continuing execution after approval.
            
        Raises:
            NoApprovalPendingError: If no approval is pending.
        """
    
    @abstractmethod
    async def reject_workflow(
        self,
        thread_id: str,
        reason: str,
    ) -> WorkflowResult:
        """Reject a workflow paused for human approval.
        
        Args:
            thread_id: The thread ID of the workflow.
            reason: The rejection reason.
            
        Returns:
            WorkflowResult with suspended state and rejection reason.
            
        Raises:
            NoApprovalPendingError: If no approval is pending.
        """
```

---

## Data Types

```python
@dataclass(frozen=True)
class WorkflowResult:
    """Result of a workflow execution."""
    final_context: WorkflowContext
    thread_id: str
    execution_time_ms: float
    node_count: int
    completed_nodes: int
    status: ExecutionState

@dataclass(frozen=True)
class WorkflowStatus:
    """Current status of a workflow execution."""
    thread_id: str
    state: ExecutionState
    current_node: Optional[str]
    completed_nodes: List[str]
    pending_nodes: List[str]
    failed_nodes: List[str]
    errors: List[ExecutionError]
    checkpoint_id: Optional[str]
```

---

## REST API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/workflow/execute` | Execute a new workflow |
| POST | `/api/v1/workflow/resume` | Resume a paused workflow |
| GET | `/api/v1/workflow/{thread_id}/status` | Get workflow status |
| POST | `/api/v1/workflow/{thread_id}/cancel` | Cancel a workflow |
| POST | `/api/v1/workflow/{thread_id}/approve` | Approve pending workflow |
| POST | `/api/v1/workflow/{thread_id}/reject` | Reject pending workflow |
