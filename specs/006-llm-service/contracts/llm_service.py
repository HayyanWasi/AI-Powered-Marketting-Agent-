"""LLM Service contract — the unified public interface.

LLMService is the single entry point for all LLM operations.
It orchestrates provider selection, retry, fallback, and template rendering.
"""

from typing import Iterator

from contracts.models import LLMRequest, LLMResponse, StreamChunk


class LLMService:
    """Unified interface for OpenAI (primary) + Gemini (fallback) LLM calls."""

    def __init__(
        self,
        primary: object | None = None,  # OpenAI client
        fallback: object | None = None,  # Gemini model
    ) -> None:
        """Lazy init: providers created on first use if None."""
        ...

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate text via primary (OpenAI) with retry+fallback.

        Flow:
          1. Resolve system_prompt from template or inline
          2. Call primary with retry (3 attempts, 1s/2s/4s backoff)
          3. If transient error exhausts retries → call fallback (Gemini)
          4. Return normalized LLMResponse

        Raises:
          LLMServiceError: both providers fail
          LLMTemplateNotFoundError: template_name not found
        """
        ...

    def generate_stream(self, request: LLMRequest) -> Iterator[StreamChunk]:
        """Stream text from primary provider only (no fallback).

        Raises:
          LLMServiceError: on provider failure
          LLMTemplateNotFoundError: template_name not found
        """
        ...


class LLMServiceError(Exception):
    """Base error for LLM service failures."""

    ...


class LLMTemplateNotFoundError(Exception):
    """Raised when a named template does not exist."""

    ...


class LLMProviderError(Exception):
    """Wraps a provider-specific error with provider name."""

    ...
