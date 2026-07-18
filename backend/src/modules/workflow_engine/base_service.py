"""Base service class for Workflow Engine services."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class WorkflowServiceBase(ABC):
    """Abstract base class for all workflow services."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the service with configuration.

        Args:
            config: Service configuration dictionary
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the service and clean up resources."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the service.

        Returns:
            Dict containing health status and details
        """
        pass
