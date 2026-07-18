"""Retry Service — manages per-node retry policies and execution."""

import asyncio
import logging
from typing import Any, Callable

from ..models import RetryPolicy, ExecutionState, ExecutionError

logger = logging.getLogger(__name__)


class RetryService:
    """Manages retry execution for failed workflow nodes."""

    def __init__(self):
        self._attempt_counts: dict[str, int] = {}

    def get_attempt_count(self, node_name: str) -> int:
        return self._attempt_counts.get(node_name, 0)

    def reset_attempts(self, node_name: str) -> None:
        self._attempt_counts.pop(node_name, None)

    def can_retry(self, node_name: str, policy: RetryPolicy) -> bool:
        attempts = self.get_attempt_count(node_name)
        return attempts < policy.max_retries

    def calculate_delay(self, node_name: str, policy: RetryPolicy) -> float:
        attempts = self.get_attempt_count(node_name)
        return policy.calculate_delay(attempts)

    def record_attempt(self, node_name: str) -> int:
        self._attempt_counts[node_name] = self.get_attempt_count(node_name) + 1
        return self._attempt_counts[node_name]

    async def execute_with_retry(
        self,
        node_name: str,
        handler: Callable,
        context: Any,
        policy: RetryPolicy,
    ) -> Any:
        last_error = None

        for attempt in range(policy.max_retries + 1):
            try:
                self.record_attempt(node_name)
                result = await handler(context)
                self.reset_attempts(node_name)
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    "Node %s attempt %d/%d failed: %s",
                    node_name,
                    attempt + 1,
                    policy.max_retries + 1,
                    e,
                )
                if attempt < policy.max_retries:
                    delay = self.calculate_delay(node_name, policy)
                    await asyncio.sleep(delay)

        raise last_error
