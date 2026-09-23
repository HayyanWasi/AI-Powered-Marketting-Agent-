"""Multi-LLM Provider Failover Router.

Routes prompt execution across providers (Groq -> Gemini -> OpenAI/Anthropic).
Catches rate limits (429) and server errors (5xx) transparently, falling back
to secondary providers to ensure the 40-60 LLM call deep pipeline never fails.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.models.llm import LLMRequest
from src.services.llm_service import LLMService, parse_json_object

logger = logging.getLogger(__name__)


class LLMRouterError(Exception):
    """Raised when all configured LLM providers fail."""


class LLMRouterService:
    """Multi-account pool failover router for Groq, OpenRouter, and Gemini."""

    DIMENSION_KEY_MAP = {
        "market": 0,
        "competitor": 0,
        "audience": 1,
        "content": 1,
        "channel": 2,
        "trend": 2,
    }

    def __init__(
        self,
        key_index: int = 0,
        dimension: str | None = None,
        llm: LLMService | None = None,
    ) -> None:
        # key_index and dimension remain accepted for existing research callers.
        # Provider/key selection belongs to the canonical LLMService.
        self.key_index = key_index
        self.dimension = dimension
        self.llm = llm or LLMService()

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1800,
        prefer_gemini: bool = False,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Generate and validate a JSON object through the canonical LLM service.

        ``timeout`` is a per-request override that the canonical service applies
        ONLY to a local Ollama provider leg; hosted providers keep their own
        timeout. Callers that omit it (the default) are unaffected.
        """
        try:
            response = await asyncio.to_thread(
                self.llm.generate,
                LLMRequest(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=True,
                    timeout=timeout,
                ),
            )
            return parse_json_object(response.text)
        except Exception as e:
            raise LLMRouterError("Structured LLM generation failed.") from e
