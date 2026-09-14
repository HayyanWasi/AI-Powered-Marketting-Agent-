"""Multi-LLM Provider Failover Router.

Routes prompt execution across providers (Groq -> Gemini -> OpenAI/Anthropic).
Catches rate limits (429) and server errors (5xx) transparently, falling back
to secondary providers to ensure the 40-60 LLM call deep pipeline never fails.
"""

from __future__ import annotations

import logging
from typing import Any

from src.config.settings import settings

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

    def __init__(self, key_index: int = 0, dimension: str | None = None) -> None:
        self.groq_keys = [
            k
            for k in [
                getattr(settings, "grok_api_key", ""),
                getattr(settings, "grok_api_key_2", ""),
                getattr(settings, "grok_api_key_3", ""),
            ]
            if k
        ]
        self.openrouter_keys = [
            k
            for k in [
                getattr(settings, "openrouter_api_key", ""),
                getattr(settings, "openrouter_api_key_2", ""),
                getattr(settings, "openrouter_api_key_3", ""),
            ]
            if k
        ]
        self.google_keys = [
            k
            for k in [
                getattr(settings, "google_api_key", ""),
                getattr(settings, "google_api_key_2", ""),
                getattr(settings, "google_api_key_3", ""),
            ]
            if k
        ]

        if dimension and dimension in self.DIMENSION_KEY_MAP:
            target_idx = self.DIMENSION_KEY_MAP[dimension]
            self.key_index = target_idx if target_idx < len(self.groq_keys) else 0
        else:
            self.key_index = key_index % max(1, len(self.groq_keys))

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        prefer_gemini: bool = False,
    ) -> dict[str, Any]:
        if prefer_gemini:
            logger.info(
                "[LLM ROUTER] Intake Chat mode: Preferring Gemini first to handle stateful chat context."
            )
            if self.google_keys:
                try:
                    result = await self._call_gemini_json(system_prompt, user_prompt)
                    if result:
                        logger.info("[LLM ROUTER SUCCESS] Gemini call succeeded.")
                        return result
                except Exception as e:
                    logger.warning(
                        "[LLM ROUTER FAILED] Gemini primary call failed (likely 429): %s. Falling back to Groq pool.",
                        e,
                    )
            else:
                logger.warning("No Google API Key found, skipping Gemini.")

        logger.info("[LLM ROUTER] Starting JSON generation (Groq -> OpenRouter -> Gemini)")

        # 1. Primary: Groq pool (fastest, free, high capacity)
        if self.groq_keys:
            num_keys = len(self.groq_keys)
            logger.info(
                "[LLM ROUTER Step 1] Attempting Groq key pool (%d keys available)...", num_keys
            )
            for offset in range(num_keys):
                idx = (self.key_index + offset) % num_keys
                api_key_groq = self.groq_keys[idx]
                try:
                    from src.modules.ai_generation.services.llm_service import LLMService

                    llm = LLMService(api_key=api_key_groq, provider="groq")
                    result = await llm.generate_json(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        raise_on_error=True,
                    )
                    if result:
                        logger.info("[LLM ROUTER Step 1 SUCCESS] Groq key #%d succeeded.", idx + 1)
                        return result
                except Exception as e:
                    logger.warning("[LLM ROUTER Step 1 FAILED] Groq key #%d failed: %s", idx + 1, e)

        # 2. Secondary: OpenRouter pool
        if self.openrouter_keys:
            num_or_keys = len(self.openrouter_keys)
            logger.info(
                "[LLM ROUTER Step 2] Attempting OpenRouter key pool (%d keys available)...",
                num_or_keys,
            )
            for offset in range(num_or_keys):
                idx = (self.key_index + offset) % num_or_keys
                or_key = self.openrouter_keys[idx]
                try:
                    result = await self._call_openrouter_json(system_prompt, user_prompt, or_key)
                    if result:
                        logger.info(
                            "[LLM ROUTER Step 2 SUCCESS] OpenRouter key #%d succeeded.", idx + 1
                        )
                        return result
                except Exception as e:
                    logger.warning(
                        "[LLM ROUTER Step 2 FAILED] OpenRouter key #%d failed: %s", idx + 1, e
                    )

        # 3. Last resort: Google Gemini (conserve free quota for intake chat only)
        if self.google_keys:
            logger.info(
                "[LLM ROUTER Step 3] All primary providers failed — attempting Gemini as last resort..."
            )
            try:
                result = await self._call_gemini_json(system_prompt, user_prompt)
                if result:
                    logger.info("[LLM ROUTER Step 3 SUCCESS] Gemini last-resort call succeeded.")
                    return result
            except Exception as e:
                logger.warning("[LLM ROUTER Step 3 FAILED] Gemini last-resort call failed: %s", e)

        if not settings.ALLOW_PLACEHOLDER_CONTENT:
            logger.error(
                "[LLM ROUTER ERROR] All LLM providers failed and ALLOW_PLACEHOLDER_CONTENT is False."
            )
            raise LLMRouterError("All LLM keys and fallback providers failed")

        logger.error("[LLM ROUTER ERROR] All LLM providers failed; returning empty dict fallback.")
        return {}

    async def _call_openrouter_json(
        self, system_prompt: str, user_prompt: str, api_key: str
    ) -> dict[str, Any]:
        """Call OpenRouter API."""
        import json
        import re

        import httpx

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": getattr(settings, "openrouter_model", "openrouter/free"),
            "messages": [
                {"role": "system", "content": f"{system_prompt}\n\nPROVIDE ONLY VALID JSON."},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            cleaned_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
            return json.loads(cleaned_text)

    async def _call_gemini_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Call Google Gemini API with pool key rotation and fallback models."""
        import json
        import re

        import httpx

        if not self.google_keys:
            raise LLMRouterError("No Google API key configured for Gemini fallback")

        last_err: Exception | None = None
        models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]

        num_keys = len(self.google_keys)
        for offset in range(num_keys):
            idx = (self.key_index + offset) % num_keys
            api_key = self.google_keys[idx]
            if not api_key:
                continue

            for model_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": f"{system_prompt}\n\nPROVIDE ONLY VALID JSON.\n\n{user_prompt}"
                                }
                            ]
                        }
                    ],
                    "generationConfig": {"response_mime_type": "application/json"},
                }
                try:
                    async with httpx.AsyncClient(timeout=20.0) as client:
                        resp = await client.post(url, json=payload)
                        resp.raise_for_status()
                        data = resp.json()
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        cleaned_text = re.sub(
                            r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE
                        )
                        return json.loads(cleaned_text)
                except Exception as e:
                    last_err = e
                    continue

        if last_err:
            raise last_err
        raise LLMRouterError("All Gemini keys failed")
