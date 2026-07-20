"""Workflow Engine Public Interface - Contract for workflow execution."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..models import WorkflowContext, WorkflowGraph


class WorkflowEngine(ABC):
    """Public interface for the Workflow Engine module.

    The Workflow Engine module provides deterministic workflow orchestration using LangGraph.
    It coordinates execution of registered workflow nodes through graph-based routing while
    remaining completely independent of business logic, AI generation, campaign management,
    and persistence.

    All external modules (Campaign Management, AI Generation) interact exclusively through
    this interface. The underlying workflow implementation (LangGraph or any future engine)
    may change without affecting dependent modules.

    This interface exposes only execution capabilities:
    - Workflow execution
    - Checkpoint management
    - Resume operations
    - Human approval processing
    - Execution status reporting

    The workflow engine knows only about:
    ```
    Node A
    ↓

    Node B
    ↓

    Node C
    ```

    It does NOT know about:
    - Campaigns
    - Marketing
    - Brands
    - Guests
    - LLMs
    - Images
    - Prompts
    - Strategy
    - Validation rules
    - Database models

    Workflow nodes are treated as black-box operations.
    """

    @abstractmethod
    async def execute_workflow(
        self,
        graph: WorkflowGraph,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
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
        pass

    @abstractmethod
    async def resume_workflow(
        self,
        thread_id: str,
        resume_value: Optional[Any] = None,
    ) -> Dict[str, Any]:
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
        pass

    @abstractmethod
    async def get_workflow_status(
        self,
        thread_id: str,
    ) -> Dict[str, Any]:
        """Get the current execution status of a workflow.

        Args:
            thread_id: The thread ID of the workflow.

        Returns:
            WorkflowStatus containing state, progress, and metadata.

        Raises:
            WorkflowNotFoundError: If no workflow exists for the thread.
        """
        pass

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
        pass

    @abstractmethod
    async def approve_workflow(
        self,
        thread_id: str,
    ) -> Dict[str, Any]:
        """Approve a workflow paused for human approval.

        Args:
            thread_id: The thread ID of the workflow.

        Returns:
            WorkflowResult continuing execution after approval.

        Raises:
            NoApprovalPendingError: If no approval is pending.
        """
        pass

    @abstractmethod
    async def reject_workflow(
        self,
        thread_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Reject a workflow paused for human approval.

        Args:
            thread_id: The thread ID of the workflow.
            reason: The rejection reason.

        Returns:
            WorkflowResult with suspended state and rejection reason.

        Raises:
            NoApprovalPendingError: If no approval is pending.
        """
        pass
