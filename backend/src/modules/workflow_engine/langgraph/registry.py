"""LangGraph Registry — connects registered node handlers into compiled graph."""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class NodeRegistry:
    """Stores registered node handlers and provides lookup by name."""

    def __init__(self):
        self._handlers: dict[str, Callable] = {}

    def register(self, name: str, handler: Callable) -> None:
        self._handlers[name] = handler
        logger.debug("Registered node: %s", name)

    def get(self, name: str) -> Callable | None:
        return self._handlers.get(name)

    def has(self, name: str) -> bool:
        return name in self._handlers

    def list_all(self) -> list[str]:
        return list(self._handlers.keys())

    def clear(self) -> None:
        self._handlers.clear()
