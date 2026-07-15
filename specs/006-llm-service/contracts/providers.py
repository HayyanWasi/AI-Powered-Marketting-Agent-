"""Internal LLM provider contracts.

These stubs define the interface each provider wrapper must implement.
Providers are NOT exported — they are internal to LLMService.
"""

from typing import Iterator

from contracts.models import LLMResponse, StreamChunk


class OpenAIProvider:
    """Wraps OpenAI SDK (openai.OpenAI)."""

    def __init__(self, client: object | None = None) -> None:
        """If client is None, create from settings.openai_api_key."""
        ...

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Standard generation via GPT-4o. Returns normalized LLMResponse."""
        ...

    def generate_stream(self, system_prompt: str, user_prompt: str) -> Iterator[StreamChunk]:
        """Streaming generation. Yields StreamChunk deltas."""
        ...


class GeminiProvider:
    """Wraps Google Gemini SDK (google.generativeai)."""

    def __init__(self, model: object | None = None) -> None:
        """If model is None, configure from settings.google_api_key."""
        ...

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Standard generation via Gemini. Returns normalized LLMResponse."""
        ...

    def generate_stream(self, system_prompt: str, user_prompt: str) -> Iterator[StreamChunk]:
        """Streaming generation. Yields StreamChunk deltas."""
        ...
