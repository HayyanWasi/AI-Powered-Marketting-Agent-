"""Base agent class for all marketing agents.

Each agent:
- Receives a GenerationContext (immutable snapshot)
- Performs its specific task
- Returns an updated GenerationContext
- Never reads from database during execution
"""

import logging
from abc import ABC, abstractmethod

from src.agents.context import GenerationContext

logger = logging.getLogger(__name__)


class AgentResult:
    """Result of an agent execution."""

    def __init__(
        self,
        success: bool,
        context: GenerationContext,
        message: str = "",
        requires_human: bool = False,
    ):
        self.success = success
        self.context = context
        self.message = message
        self.requires_human = requires_human

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"AgentResult({status}: {self.message})"


class BaseAgent(ABC):
    """Base class for all marketing agents.

    Subclasses must implement execute() which:
    1. Reads from context
    2. Performs agent-specific logic
    3. Returns a new context with updates
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    def execute(self, context: GenerationContext) -> AgentResult:
        """Execute the agent's task.

        Args:
            context: Immutable snapshot of all workflow data

        Returns:
            AgentResult with updated context
        """
        ...

    def _update_context(self, context: GenerationContext, **kwargs) -> GenerationContext:
        """Create a new context with updates (immutable pattern).

        Since GenerationContext uses frozen dataclasses for sub-objects,
        we create a new context with updated fields.
        """
        from dataclasses import replace

        return replace(context, **kwargs)
