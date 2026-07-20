"""Error handling utilities for Workflow Engine."""

from typing import Dict, Any


class WorkflowEngineError(Exception):
    """Base class for all workflow engine errors."""

    pass


class CircuitDependencyError(WorkflowEngineError):
    """Raised when circular dependency is detected."""

    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = "circuit_dependency"


class MissingEntryNodeError(WorkflowEngineError):
    """Raised when entry node is missing."""

    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = "missing_entry_node"


class CheckpointError(WorkflowEngineError):
    """Base class for checkpoint-related errors."""

    pass


class CheckpointNotFoundError(CheckpointError):
    """Raised when checkpoint is not found."""

    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = "checkpoint_not_found"


class WorkflowError(WorkflowEngineError):
    """Base class for workflow execution errors."""

    pass


class WorkflowNotFoundError(WorkflowError):
    """Raised when workflow is not found."""

    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = "workflow_not_found"


class NoApprovalPendingError(WorkflowEngineError):
    """Raised when no approval is pending."""

    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = "no_approval_pending"


class WorkflowExecutionError(Exception):
    """Error raised during workflow execution."""

    def __init__(self, message: str, error_code: str = "workflow_execution_failed"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class GraphValidationError(Exception):
    """Error raised during graph validation."""

    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = "graph_validation_failed"
        self.errors = []

    def add_error(self, error_code: str, message: str, severity: str = "error"):
        """Add a validation error."""
        self.errors.append(
            {
                "code": error_code,
                "message": message,
                "severity": severity,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation errors to dictionary representation."""
        return {
            "error_code": self.error_code,
            "message": self.args[0],
            "errors": self.errors,
            "valid": False,
        }
