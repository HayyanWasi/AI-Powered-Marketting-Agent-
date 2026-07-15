import logging
import time
from collections.abc import Callable
from typing import Any, Iterator

from src.config.prompts import render_template
from src.config.settings import settings
from src.models.llm import LLMRequest, LLMResponse, StreamChunk, TokenUsage

logger = logging.getLogger(__name__)

OPENAI_MODEL = "gpt-4o"
GEMINI_MODEL = "models/gemini-1.5-flash"
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]


class LLMServiceError(Exception):
    pass


class LLMProviderError(Exception):
    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class LLMTemplateNotFoundError(Exception):
    pass


def _is_transient_error(exc: Exception) -> bool:
    exc_type = type(exc).__name__
    transient_names = {"RateLimitError", "APITimeoutError", "APIConnectionError", "ServerError"}
    if exc_type in transient_names:
        return True
    msg = str(exc).lower()
    return any(kw in msg for kw in ("rate limit", "timeout", "500", "502", "503", "504"))


def _retry_with_backoff(
    func: Callable[..., LLMResponse],
    *args: Any,
    **kwargs: Any,
) -> LLMResponse:
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if not _is_transient_error(e):
                raise
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.warning("Retry %d/%d after %.1fs: %s", attempt, MAX_RETRIES, delay, e)
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]


class OpenAIProvider:
    def __init__(self, client: Any = None) -> None:
        self._client = client
        self._initialized = False

    def _ensure_client(self) -> None:
        if not self._initialized:
            from openai import OpenAI

            if self._client is None:
                self._client = OpenAI(api_key=settings.openai_api_key)
            self._initialized = True

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        self._ensure_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        completion = self._client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            stream=False,
        )
        choice = completion.choices[0]
        usage = completion.usage

        return LLMResponse(
            text=choice.message.content or "",
            token_usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                provider="openai",
            ),
            provider="openai",
            model=OPENAI_MODEL,
        )

    def generate_stream(self, system_prompt: str, user_prompt: str) -> Iterator[StreamChunk]:
        self._ensure_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        stream = self._client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            content = delta.content if delta and delta.content else ""
            finished = chunk.choices[0].finish_reason is not None if chunk.choices else False
            if content or finished:
                yield StreamChunk(content=content or "", finished=finished)


class GeminiProvider:
    def __init__(self, model: Any = None) -> None:
        self._model = model
        self._initialized = False

    def _ensure_model(self) -> None:
        if not self._initialized:
            import google.generativeai as genai

            if self._model is None:
                genai.configure(api_key=settings.google_api_key)  # type: ignore[attr-defined]
                self._model = genai.GenerativeModel(GEMINI_MODEL)  # type: ignore[attr-defined]
            self._initialized = True

    def _model_for_prompt(self, system_prompt: str) -> Any:
        if not system_prompt:
            return self._model
        model = type(self._model)(GEMINI_MODEL, system_instruction=system_prompt)
        model._client = self._model._client
        return model

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        self._ensure_model()
        response = self._model_for_prompt(system_prompt).generate_content(user_prompt, stream=False)

        usage_meta = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else 0
        completion_tokens = getattr(usage_meta, "candidates_token_count", 0) if usage_meta else 0
        total_tokens = getattr(usage_meta, "total_token_count", 0) if usage_meta else 0

        return LLMResponse(
            text=response.text or "",
            token_usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                provider="gemini",
            ),
            provider="gemini",
            model=GEMINI_MODEL,
        )

    def generate_stream(self, system_prompt: str, user_prompt: str) -> Iterator[StreamChunk]:
        self._ensure_model()
        for chunk in self._model_for_prompt(system_prompt).generate_content(
            user_prompt, stream=True
        ):
            content = getattr(chunk, "text", "") or ""
            yield StreamChunk(content=content, finished=False)
        yield StreamChunk(content="", finished=True)


class LLMService:
    def __init__(
        self,
        primary: OpenAIProvider | None = None,
        fallback: GeminiProvider | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def _get_primary(self) -> OpenAIProvider:
        if self._primary is None:
            self._primary = OpenAIProvider()
        return self._primary

    def _get_fallback(self) -> GeminiProvider:
        if self._fallback is None:
            self._fallback = GeminiProvider()
        return self._fallback

    def _resolve_system_prompt(self, request: LLMRequest) -> str | None:
        if request.template_name:
            try:
                return render_template(request.template_name, request.template_variables)
            except KeyError as e:
                raise LLMTemplateNotFoundError(str(e)) from e
        return request.system_prompt

    def generate(self, request: LLMRequest) -> LLMResponse:
        system_prompt = self._resolve_system_prompt(request) or ""

        try:
            return _retry_with_backoff(
                self._get_primary().generate, system_prompt, request.user_prompt
            )
        except Exception as primary_exc:
            logger.warning("Primary provider failed: %s", primary_exc)
            if not _is_transient_error(primary_exc):
                raise LLMProviderError("openai", str(primary_exc)) from primary_exc

            logger.info("Falling back to Gemini")
            try:
                return self._get_fallback().generate(system_prompt, request.user_prompt)
            except Exception as fallback_exc:
                raise LLMServiceError(
                    f"Both providers failed. OpenAI: {primary_exc}. " f"Gemini: {fallback_exc}"
                ) from fallback_exc

    def generate_stream(self, request: LLMRequest) -> Iterator[StreamChunk]:
        system_prompt = self._resolve_system_prompt(request) or ""
        return self._get_primary().generate_stream(system_prompt, request.user_prompt)
