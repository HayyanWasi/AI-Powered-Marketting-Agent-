"""Core workflow data models for Workflow Engine module.

This module defines the core data structures used by the workflow engine
for task execution, state management, and workflow orchestration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ExecutionState(str, Enum):
    """Enumeration of possible workflow execution states."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeStatus(str, Enum):
    """Status of individual workflow nodes."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalStatus(str, Enum):
    """Status of human approval requests."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WorkflowNodeType(str, Enum):
    """Types of workflow nodes."""

    EXECUTION = "execution"
    APPROVAL = "approval"
    RETRY = "retry"
    CHECKPOINT = "checkpoint"
    ROUTE = "route"


class ErrorCode(str, Enum):
    """Standard error codes for workflow operations."""

    INVALID_GRAPH = "invalid_graph"
    NODE_FAILED = "node_failed"
    CHECKPOINT_FAILED = "checkpoint_failed"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    WORKFLOW_NOT_FOUND = "workflow_not_found"
    INVALID_CHECKPOINT = "invalid_checkpoint"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"
    CYCLE_DETECTED = "cycle_detected"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"


class WorkflowErrorCode(str, Enum):
    """Workflow-specific error codes."""

    WORKFLOW_NOT_FOUND = "workflow_not_found"
    NODE_NOT_FOUND = "node_not_found"
    INVALID_TRANSITION = "invalid_transition"
    EXECUTION_TIMEOUT = "execution_timeout"
    UNEXPECTED_INPUT = "unexpected_input"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"


class GraphValidationError(BaseException):
    """Raised when workflow graph validation fails."""

    pass


class CircleDependencyError(GraphValidationError):
    """Raised when circular dependency is detected."""

    pass


class MissingEntryNodeError(GraphValidationError):
    """Raised when entry node is missing."""

    pass


class CheckpointError(Exception):
    """Base class for checkpoint-related errors."""

    pass


class CheckpointNotFoundError(CheckpointError):
    """Raised when checkpoint is not found."""

    pass


class ResumeError(Exception):
    """Base class for resume-related errors."""

    pass


class ApprovalError(Exception):
    """Base class for approval-related errors."""

    pass


class NoApprovalPendingError(ApprovalError):
    """Raised when no approval is pending."""

    pass


class WorkflowExecutionError(Exception):
    """Base class for workflow execution errors."""

    pass


class WorkflowNotFoundError(WorkflowExecutionError):
    """Raised when workflow is not found."""

    pass


class InvalidCheckpointError(WorkflowExecutionError):
    """Raised when checkpoint is invalid."""

    pass


@dataclass(frozen=True)
class WorkflowContext:
    """Immutable execution context for workflow nodes.

    Immutable execution state shared across workflow nodes. Each node receives
    an immutable WorkflowContext and returns a new instance with its outputs.
    Existing context is never modified in place.
    """

    workflow_id: str
    thread_id: str
    state: ExecutionState
    node_outputs: Dict[str, Any]
    errors: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    current_node: Optional[str]

    def __post_init__(self):
        if not self.workflow_id:
            raise ValueError("workflow_id cannot be empty")
        if self.state not in ExecutionState.__members__.values():
            raise ValueError(f"Invalid state: {self.state}")

    @classmethod
    def create(
        cls,
        workflow_id: str,
        thread_id: str,
        state: ExecutionState = ExecutionState.PENDING,
        node_outputs: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        current_node: Optional[str] = None,
    ) -> "WorkflowContext":
        """Create a new WorkflowContext.

        Args:
            workflow_id: Unique identifier for this workflow execution
            thread_id: LangGraph thread ID for checkpoint isolation
            state: Initial execution state
            node_outputs: Initial node outputs
            errors: Initial errors
            metadata: Initial metadata
            current_node: Current node name

        Returns:
            New WorkflowContext instance
        """
        return cls(
            workflow_id=workflow_id,
            thread_id=thread_id,
            state=state,
            node_outputs=node_outputs or {},
            errors=errors or [],
            metadata=metadata or {},
            current_node=current_node,
        )

    def with_updates(
        self,
        workflow_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        state: Optional[ExecutionState] = None,
        node_outputs: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        current_node: Optional[str] = None,
    ) -> "WorkflowContext":
        """Create a new WorkflowContext with updated fields.

        Args:
            workflow_id: Updated workflow_id (preserve if None)
            thread_id: Updated thread_id (preserve if None)
            state: Updated state (preserve if None)
            node_outputs: Updated node_outputs (preserve if None)
            errors: Updated errors (preserve if None)
            metadata: Updated metadata (preserve if None)
            current_node: Updated current_node (preserve if None)

        Returns:
            New WorkflowContext with updated fields
        """
        return WorkflowContext.create(
            workflow_id=workflow_id or self.workflow_id,
            thread_id=thread_id or self.thread_id,
            state=state or self.state,
            node_outputs={**self.node_outputs, **(node_outputs or {})},
            errors=self.errors + (errors or []),
            metadata={**self.metadata, **(metadata or {})},
            current_node=current_node or self.current_node,
        )


@dataclass(frozen=True)
class WorkflowNode:
    """A registered executable unit that receives an immutable WorkflowContext,
    performs a single task, and returns a new immutable WorkflowContext.

    Each node defines its own retry policy (retry count, retry delay, retry strategy).
    """

    name: str
    description: str
    handler: callable
    retry_policy: Dict[str, Any]
    timeout_seconds: Optional[float]
    requires_approval: bool

    def __post_init__(self):
        if not self.name:
            raise ValueError("name cannot be empty")
        if not callable(self.handler):
            raise ValueError("handler must be callable")
        if self.retry_policy:
            if self.retry_policy.get("max_retries", 0) < 0:
                raise ValueError("max_retries cannot be negative")
            if self.retry_policy.get("delay_seconds", 0) < 0:
                raise ValueError("delay_seconds cannot be negative")


@dataclass
class WorkflowGraph:
    """Complete workflow definition containing registered nodes, execution edges,
    routing rules, and entry points.
    """

    graph_id: str
    nodes: Dict[str, WorkflowNode]
    entry_point: str
    edges: List[Dict[str, Any]]
    conditional_edges: List[Dict[str, Any]]
    terminal_nodes: List[str]

    def __post_init__(self):
        if not self.graph_id:
            raise ValueError("graph_id cannot be empty")
        if self.entry_point not in self.nodes:
            raise MissingEntryNodeError(f"Entry node {self.entry_point} not found in graph")
        for node_name in self.nodes:
            if node_name not in self.nodes:
                raise ValueError(f"Node {node_name} referenced in graph but not defined")
        for edge in self.edges:
            if edge["source"] not in self.nodes:
                raise ValueError(f"Source node {edge['source']} not found in graph")
            if edge["target"] not in self.nodes:
                raise ValueError(f"Target node {edge['target']} not found in graph")
        for edge in self.conditional_edges:
            if edge["source"] not in self.nodes:
                raise ValueError(f"Source node {edge['source']} not found in graph")

    @classmethod
    def validate_graph(cls, graph: "WorkflowGraph") -> None:
        """Validate workflow graph structure.

        Args:
            graph: WorkflowGraph to validate

        Raises:
            MissingEntryNodeError: If entry node is missing
            CircleDependencyError: If circular dependency is detected
            ValueError: If other validation errors occur
        """
        if not graph.entry_point:
            raise MissingEntryNodeError("Entry point is missing")

        # Check for cycles
        visited = set()
        path = set()

        def dfs(node_name: str):
            if node_name in path:
                cycle = list(path) + [node_name]
                raise CircleDependencyError(f"Circular dependency detected: {' -> '.join(cycle)}")
            if node_name in visited:
                return

            visited.add(node_name)
            path.add(node_name)

            # Check outgoing edges
            for edge in graph.edges:
                if edge["source"] == node_name:
                    dfs(edge["target"])

            for edge in graph.conditional_edges:
                if edge["source"] == node_name:
                    dfs(edge["target"])

            path.remove(node_name)

        dfs(graph.entry_point)

    @classmethod
    def detect_cycles(cls, graph: "WorkflowGraph") -> List[List[str]]:
        """Detect circular dependencies in workflow graph.

        Args:
            graph: Workflow graph to analyze

        Returns:
            List of cycle paths found
        """
        cycles = []
        visited = set()
        path = []
        path_set = set()

        def dfs(node_name: str):
            if node_name in path_set:
                cycle_start = path.index(node_name)
                cycles.append(path[cycle_start:] + [node_name])
                return

            if node_name in visited:
                return

            visited.add(node_name)
            path.append(node_name)
            path_set.add(node_name)

            # Check outgoing edges
            for edge in graph.edges:
                if edge["source"] == node_name:
                    dfs(edge["target"])

            for edge in graph.conditional_edges:
                if edge["source"] == node_name:
                    dfs(edge["target"])

            path.pop()
            path_set.remove(node_name)

        for node_name in graph.nodes:
            if node_name not in visited:
                dfs(node_name)

        return cycles


@dataclass(frozen=True)
class RetryPolicy:
    """Per-node retry configuration.

    Attributes:
        max_retries: Maximum retry attempts
        delay_seconds: Delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
        max_delay_seconds: Maximum delay cap
    """

    max_retries: int
    delay_seconds: float
    backoff_multiplier: float = 1.0
    max_delay_seconds: Optional[float] = None

    def __post_init__(self):
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds cannot be negative")
        if self.max_delay_seconds is not None and self.max_delay_seconds < 0:
            raise ValueError("max_delay_seconds cannot be negative")
        if self.backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be >= 1.0")

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt.

        Args:
            attempt: Retry attempt number (0 for first)

        Returns:
            Delay in seconds
        """
        delay = self.delay_seconds * (self.backoff_multiplier**attempt)
        return min(delay, self.max_delay_seconds) if self.max_delay_seconds else delay


@dataclass(frozen=True)
class ExecutionCheckpoint:
    """Serialized workflow state captured after successful node execution.

    Managed internally by LangGraph — the engine never reads/writes checkpoint
    data directly.
    """

    thread_id: str
    checkpoint_id: str
    timestamp: datetime
    node_name: str

    def __post_init__(self):
        if not self.thread_id:
            raise ValueError("thread_id cannot be empty")
        if not self.checkpoint_id:
            raise ValueError("checkpoint_id cannot be empty")
        if not self.node_name:
            raise ValueError("node_name cannot be empty")


@dataclass
class ApprovalRequest:
    """Represents a workflow suspension awaiting human approval.

    Attributes:
        thread_id: Workflow thread ID
        node_name: Node requesting approval
        request_data: Data presented to approver
        status: Current status
        rejection_reason: Reason if rejected
        created_at: When request was created
        resolved_at: When request was resolved
    """

    thread_id: str
    node_name: str
    request_data: Dict[str, Any]
    status: ApprovalStatus
    rejection_reason: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    def __post_init__(self):
        if not self.thread_id:
            raise ValueError("thread_id cannot be empty")
        if not self.node_name:
            raise ValueError("node_name cannot be empty")
        if not self.request_data:
            raise ValueError("request_data cannot be empty")
        if self.status not in ApprovalStatus.__members__.values():
            raise ValueError(f"Invalid approval status: {self.status}")
        if self.status == ApprovalStatus.REJECTED and not self.rejection_reason:
            raise ValueError("rejection_reason is required when status is REJECTED")
        if self.resolved_at and self.resolved_at < self.created_at:
            raise ValueError("resolved_at cannot be before created_at")

    def approve(self) -> None:
        """Approve this approval request."""
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(f"Cannot approve approval request with status: {self.status}")
        self.status = ApprovalStatus.APPROVED
        self.resolved_at = datetime.now()

    def reject(self, reason: str) -> None:
        """Reject this approval request.

        Args:
            reason: Rejection reason
        """
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(f"Cannot reject approval request with status: {self.status}")
        self.status = ApprovalStatus.REJECTED
        self.rejection_reason = reason
        self.resolved_at = datetime.now()


@dataclass(frozen=True)
class ExecutionError:
    """Structured error record for workflow failures.

    Attributes:
        node_name: Node where error occurred
        error_code: Machine-readable error code
        message: Human-readable error message
        retry_count: Number of retries attempted
        timestamp: When error occurred
        recoverable: Whether error is recoverable via retry/resume
    """

    node_name: str
    error_code: str
    message: str
    retry_count: int
    timestamp: datetime
    recoverable: bool

    def __post_init__(self):
        if not self.node_name:
            raise ValueError("node_name cannot be empty")
        if not self.error_code:
            raise ValueError("error_code cannot be empty")
        if not self.message:
            raise ValueError("message cannot be empty")
        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")


@dataclass(frozen=True)
class WorkflowResult:
    """Result of a workflow execution.

    Attributes:
        final_context: Final workflow context
        thread_id: Workflow thread ID
        execution_time_ms: Execution time in milliseconds
        node_count: Total number of nodes in workflow
        completed_nodes: Number of completed nodes
        status: Final execution state
    """

    final_context: WorkflowContext
    thread_id: str
    execution_time_ms: float
    node_count: int
    completed_nodes: int
    status: ExecutionState

    def __post_init__(self):
        if self.execution_time_ms < 0:
            raise ValueError("execution_time_ms cannot be negative")
        if self.node_count < 0:
            raise ValueError("node_count cannot be negative")
        if self.completed_nodes < 0:
            raise ValueError("completed_nodes cannot be negative")
        if self.completed_nodes > self.node_count:
            raise ValueError("completed_nodes cannot exceed node_count")


@dataclass(frozen=True)
class WorkflowStatus:
    """Current status of a workflow execution.

    Attributes:
        thread_id: Workflow thread ID
        state: Current execution state
        current_node: Current node name
        completed_nodes: List of completed node names
        pending_nodes: List of pending node names
        failed_nodes: List of failed node names
        errors: List of execution errors
        checkpoint_id: Current checkpoint ID
    """

    thread_id: str
    state: ExecutionState
    current_node: Optional[str]
    completed_nodes: List[str]
    pending_nodes: List[str]
    failed_nodes: List[str]
    errors: List[ExecutionError]
    checkpoint_id: Optional[str]

    def __post_init__(self):
        if not self.thread_id:
            raise ValueError("thread_id cannot be empty")
        if self.current_node and self.current_node in self.completed_nodes:
            raise ValueError("current_node cannot be in completed_nodes")
        if self.current_node and self.current_node in self.failed_nodes:
            raise ValueError("current_node cannot be in failed_nodes")

        # Validate consistency
        all_nodes = set(self.completed_nodes) | set(self.pending_nodes) | set(self.failed_nodes)
        if self.current_node:
            all_nodes.add(self.current_node)

        if len(all_nodes) != len(self.completed_nodes) + len(self.pending_nodes) + len(
            self.failed_nodes
        ) + (1 if self.current_node else 0):
            raise ValueError("Status data is inconsistent")
