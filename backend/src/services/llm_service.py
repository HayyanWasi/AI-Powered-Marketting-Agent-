import logging
import time
from collections.abc import Callable, Iterator
from typing import Any

from src.config.prompts import render_template
from src.config.settings import settings
from src.models.llm import LLMRequest, LLMResponse, StreamChunk, TokenUsage

logger = logging.getLogger(__name__)

GEMINI_MODEL = "models/gemini-3.5-flash"
GROK_MODEL = "llama-3.3-70b-versatile"
GROK_BASE_URL = "https://api.groq.com/openai/v1"
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


class GrokProvider:
    def __init__(self, client: Any = None) -> None:
        self._client = client
        self._initialized = False

    def _ensure_client(self) -> None:
        if not self._initialized:
            from openai import OpenAI

            if self._client is None:
                self._client = OpenAI(
                    api_key=settings.grok_api_key,
                    base_url=GROK_BASE_URL,
                )
            self._initialized = True

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        self._ensure_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        completion = self._client.chat.completions.create(
            model=GROK_MODEL,
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
                provider="grok",
            ),
            provider="grok",
            model=GROK_MODEL,
        )


class LLMService:
    def __init__(
        self,
        primary: GrokProvider | None = None,
        fallback: GeminiProvider | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def _get_primary(self) -> GrokProvider:
        if self._primary is None:
            self._primary = GrokProvider()
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
        start = time.perf_counter()

        try:
            response = _retry_with_backoff(
                self._get_primary().generate, system_prompt, request.user_prompt
            )
        except Exception as primary_exc:
            # Auth errors should not fall back - they indicate invalid credentials
            if self._is_auth_error(primary_exc):
                self._record_telemetry(
                    request, system_prompt, None, start, "grok", GROK_MODEL, str(primary_exc)
                )
                raise LLMProviderError("grok", str(primary_exc)) from primary_exc

            logger.warning("Primary provider (Groq) failed: %s", primary_exc)

            logger.info("Falling back to Gemini")
            fallback_start = time.perf_counter()
            try:
                response = self._get_fallback().generate(system_prompt, request.user_prompt)
            except Exception as fallback_exc:
                self._record_telemetry(
                    request,
                    system_prompt,
                    None,
                    fallback_start,
                    "gemini",
                    GEMINI_MODEL,
                    str(fallback_exc),
                )
                raise LLMServiceError(
                    f"Both providers failed. Groq: {primary_exc}. Gemini: {fallback_exc}"
                ) from fallback_exc
            self._record_telemetry(
                request, system_prompt, response, fallback_start, "gemini", GEMINI_MODEL, None
            )
            return response

        self._record_telemetry(request, system_prompt, response, start, "grok", GROK_MODEL, None)
        return response

    @staticmethod
    def _record_telemetry(
        request: LLMRequest,
        system_prompt: str,
        response: LLMResponse | None,
        start: float,
        model_name: str,
        model_version: str,
        error: str | None,
    ) -> None:
        """Attach this call to the active workflow trace, if any.

        Never raises — telemetry must not affect generation (FR-011).
        """
        try:
            from src.modules.operations.context import get_execution_context

            ctx = get_execution_context()
            if ctx is None:
                return

            trace_id, workflow_id = ctx
            from src.api.dependencies import get_operations_service

            operations = get_operations_service()
            usage = response.token_usage if response else None
            operations.record_ai_request_sync(
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version_id=operations.register_or_get_prompt_version(
                    name=request.prompt_name or request.template_name or "adhoc",
                    template=system_prompt,
                ),
                prompt_name=request.prompt_name or request.template_name or "adhoc",
                model_name=model_name,
                model_version=model_version,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                latency_ms=int((time.perf_counter() - start) * 1000),
                status="error" if error else "success",
                error_message=error,
            )
        except Exception as e:
            logger.warning("LLM telemetry recording failed: %s", e)

    @staticmethod
    def _is_auth_error(exc: Exception) -> bool:
        """Check if an error is an authentication/authorization error."""
        msg = str(exc).lower()
        auth_keywords = (
            "invalid api key",
            "unauthorized",
            "authentication",
            "forbidden",
            "401",
            "403",
        )
        return any(kw in msg for kw in auth_keywords)

    def generate_stream(self, request: LLMRequest) -> Iterator[StreamChunk]:
        system_prompt = self._resolve_system_prompt(request) or ""
        return self._get_primary().generate_stream(system_prompt, request.user_prompt)
