"""Constants for Workflow Engine."""

from enum import Enum


class ExecutionStatus(str, Enum):
    """Status of workflow execution."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    RETRYING = "retrying"


class NodeStatus(str, Enum):
    """Status of individual workflow nodes."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
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


class CheckpointStatus(str, Enum):
    """Status of workflow checkpoints."""

    ACTIVE = "active"
    FINAL = "final"
    ARCHIVED = "archived"
    EXPIRED = "expired"
