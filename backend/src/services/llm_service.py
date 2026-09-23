from __future__ import annotations

import inspect
import json
import logging
import re
import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

from src.config.prompts import render_template
from src.config.settings import settings
from src.models.llm import LLMRequest, LLMResponse, StreamChunk, TokenUsage

logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GROK_MODEL = getattr(settings, "groq_model", "openai/gpt-oss-120b")
GROK_BASE_URL = "https://api.groq.com/openai/v1"
GEMINI_MODEL = getattr(settings, "gemini_model", "gemini-3.6-flash")
MAX_RETRIES = 4
RETRY_DELAYS = [5, 10, 20, 30]
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]
PROVIDER_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_OUTPUT_TOKENS = 2048
GROQ_MAX_OUTPUT_TOKENS = 2400

_provider_rotation_lock = threading.Lock()
_provider_rotation_index = 0
# Per-credential cooldown, keyed by id(provider_instance) so one rate-limited API
# key rolls over to its sibling key of the same provider without disabling the
# whole provider.
_provider_unavailable_until: dict[int, float] = {}


def _remote_mode() -> bool:
    """True when the app routes all LLM work to remote providers (no Ollama).

    Driven by LLM_MODE (default "remote"). Only the explicit legacy values
    ("ollama"/"local"/"hybrid") re-enable the Ollama-primary paths, so a typo or
    unset value stays on the safe remote-only default.
    """
    return (settings.llm_mode or "remote").strip().lower() not in ("ollama", "local", "hybrid")


class LLMServiceError(Exception):
    pass


class LLMProviderError(Exception):
    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class LLMTemplateNotFoundError(Exception):
    pass


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse one JSON object from a provider response or fail explicitly."""
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fenced:
        cleaned = fenced.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        raise LLMServiceError("The LLM response did not contain a JSON object.")

    try:
        value = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMServiceError("The LLM response contained invalid JSON.") from exc
    if not isinstance(value, dict):
        raise LLMServiceError("The LLM response must be a JSON object.")
    return value


def _is_rate_limit_error(exc: Exception) -> bool:
    exc_type = type(exc).__name__.lower()
    if exc_type in {"ratelimiterror", "resourceexhausted"}:
        return True
    msg = str(exc).lower()
    return any(
        marker in msg
        for marker in ("rate limit", "rate-limit", "429", "quota exceeded", "resource exhausted")
    )


def _is_transient_error(exc: Exception) -> bool:
    exc_type = type(exc).__name__
    transient_names = {"RateLimitError", "APITimeoutError", "APIConnectionError", "ServerError"}
    if exc_type in transient_names:
        return True
    msg = str(exc).lower()
    return any(kw in msg for kw in ("rate limit", "timeout", "500", "502", "503", "504"))


def _is_timeout_error(exc: Exception) -> bool:
    """A request that hit the client/provider HTTP timeout specifically."""
    if type(exc).__name__ == "APITimeoutError":
        return True
    msg = str(exc).lower()
    return "timed out" in msg or "timeout" in msg


def _retry_with_backoff(
    func: Callable[..., LLMResponse],
    *args: Any,
    retry_on_timeout: bool = True,
    **kwargs: Any,
) -> LLMResponse:
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            # A second call to the same provider makes quota pressure worse.
            # Let the service immediately try the next provider instead.
            if _is_rate_limit_error(e):
                raise
            # For a single-GPU local model, a timed-out non-streaming generation
            # may still be running on the GPU; resending the same heavy request
            # only piles more work onto the queue. Fail the attempt instead.
            if not retry_on_timeout and _is_timeout_error(e):
                raise
            if not _is_transient_error(e):
                raise
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.warning("Retry %d/%d after %.1fs: %s", attempt, MAX_RETRIES, delay, e)
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]


class GeminiProvider:
    def __init__(self, model: Any = None, api_key: str | None = None) -> None:
        self._model = model
        self._api_key = api_key
        self._initialized = False

    def _ensure_model(self) -> None:
        if not self._initialized:
            import google.generativeai as genai

            if self._model is None:
                keys = [
                    k
                    for k in (
                        settings.google_api_key,
                        settings.google_api_key_2,
                        settings.google_api_key_3,
                    )
                    if k
                ]
                active_key = keys[0] if keys else None
                active_key = self._api_key
                if not active_key:
                    keys = [
                        k
                        for k in (
                            settings.google_api_key,
                            settings.google_api_key_2,
                            settings.google_api_key_3,
                        )
                        if k
                    ]
                    active_key = keys[0] if keys else None
                if not active_key:
                    raise LLMProviderError("gemini", "Gemini unavailable/skipped (missing API key)")
                genai.configure(api_key=active_key)  # type: ignore[attr-defined]
                self._model = genai.GenerativeModel(GEMINI_MODEL)  # type: ignore[attr-defined]
            self._initialized = True

    def _model_for_prompt(self, system_prompt: str) -> Any:
        if not system_prompt:
            return self._model
        model = type(self._model)(GEMINI_MODEL, system_instruction=system_prompt)
        model._client = self._model._client
        return model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self._ensure_model()
        generation_config: dict[str, Any] = {
            "max_output_tokens": max_tokens or DEFAULT_MAX_OUTPUT_TOKENS
        }
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        try:
            response = self._model_for_prompt(system_prompt).generate_content(
                user_prompt,
                stream=False,
                request_options={"timeout": PROVIDER_TIMEOUT_SECONDS},
                generation_config=generation_config,
            )
        except Exception as exc:
            if json_mode and "response_mime_type" in str(exc):
                generation_config.pop("response_mime_type", None)
                response = self._model_for_prompt(system_prompt).generate_content(
                    user_prompt,
                    stream=False,
                    request_options={"timeout": PROVIDER_TIMEOUT_SECONDS},
                    generation_config=generation_config,
                )
            else:
                raise

        usage_meta = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else 0
        completion_tokens = getattr(usage_meta, "candidates_token_count", 0) if usage_meta else 0
        total_tokens = getattr(usage_meta, "total_token_count", 0) if usage_meta else 0

        candidate = response.candidates[0] if getattr(response, "candidates", None) else None
        raw_finish = getattr(candidate, "finish_reason", None)
        finish_reason = (
            getattr(raw_finish, "name", str(raw_finish)) if raw_finish is not None else None
        )

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
            finish_reason=finish_reason,
        )

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> Iterator[StreamChunk]:
        self._ensure_model()
        for chunk in self._model_for_prompt(system_prompt).generate_content(
            user_prompt,
            stream=True,
            request_options={"timeout": PROVIDER_TIMEOUT_SECONDS},
            generation_config={"max_output_tokens": max_tokens or DEFAULT_MAX_OUTPUT_TOKENS},
        ):
            content = getattr(chunk, "text", "") or ""
            yield StreamChunk(content=content, finished=False)
        yield StreamChunk(content="", finished=True)


class OpenRouterProvider:
    def __init__(self, client: Any = None, api_key: str | None = None) -> None:
        self._client = client
        self._api_key = api_key
        self._initialized = False

    def _ensure_client(self) -> None:
        if not self._initialized:
            from openai import OpenAI

            if self._client is None:
                keys = [
                    k
                    for k in (
                        settings.openrouter_api_key,
                        settings.openrouter_api_key_2,
                        settings.openrouter_api_key_3,
                    )
                    if k
                ]
                active_key = keys[0] if keys else None
                active_key = self._api_key
                if not active_key:
                    keys = [
                        k
                        for k in (
                            settings.openrouter_api_key,
                            settings.openrouter_api_key_2,
                            settings.openrouter_api_key_3,
                        )
                        if k
                    ]
                    active_key = keys[0] if keys else None
                if not active_key:
                    raise LLMProviderError(
                        "openrouter", "OpenRouter unavailable/skipped (missing API key)"
                    )
                self._client = OpenAI(
                    api_key=active_key,
                    base_url=OPENROUTER_BASE_URL,
                    timeout=PROVIDER_TIMEOUT_SECONDS,
                    max_retries=0,
                )
            self._initialized = True

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self._ensure_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        params: dict[str, Any] = {
            "model": settings.openrouter_model,
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
        }
        if json_mode:
            params["response_format"] = {"type": "json_object"}

        try:
            completion = self._client.chat.completions.create(**params)
        except Exception as exc:
            if json_mode and "response_format" in str(exc):
                params.pop("response_format", None)
                completion = self._client.chat.completions.create(**params)
            else:
                raise

        choice = completion.choices[0]
        usage = completion.usage
        finish_reason = getattr(choice, "finish_reason", None)

        return LLMResponse(
            text=choice.message.content or "",
            token_usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                provider="openrouter",
            ),
            provider="openrouter",
            model=settings.openrouter_model,
            finish_reason=finish_reason,
        )

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> Iterator[StreamChunk]:
        self._ensure_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        stream = self._client.chat.completions.create(
            model=settings.openrouter_model,
            messages=messages,
            stream=True,
            max_tokens=max_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
        )
        for chunk in stream:
            content = (
                chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else ""
            )
            if content:
                yield StreamChunk(content=content, finished=False)
        yield StreamChunk(content="", finished=True)


class GroqProvider:
    def __init__(self, client: Any = None, api_key: str | None = None) -> None:
        self._client = client
        self._api_key = api_key
        self._initialized = False

    def _ensure_client(self) -> None:
        if not self._initialized:
            from openai import OpenAI

            if self._client is None:
                keys = [
                    k
                    for k in (
                        settings.grok_api_key,
                        settings.grok_api_key_2,
                        settings.grok_api_key_3,
                    )
                    if k
                ]
                active_key = keys[0] if keys else None
                active_key = self._api_key
                if not active_key:
                    keys = [
                        k
                        for k in (
                            settings.grok_api_key,
                            settings.grok_api_key_2,
                            settings.grok_api_key_3,
                        )
                        if k
                    ]
                    active_key = keys[0] if keys else None
                if not active_key:
                    raise LLMProviderError("groq", "Groq unavailable/skipped (missing API key)")
                self._client = OpenAI(
                    api_key=active_key,
                    base_url=GROK_BASE_URL,
                    timeout=PROVIDER_TIMEOUT_SECONDS,
                    max_retries=0,
                )
            self._initialized = True

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self._ensure_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        params: dict[str, Any] = {
            "model": GROK_MODEL,
            "messages": messages,
            "stream": False,
            "max_tokens": min(
                max_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
                GROQ_MAX_OUTPUT_TOKENS,
            ),
        }
        if json_mode:
            params["response_format"] = {"type": "json_object"}

        try:
            completion = self._client.chat.completions.create(**params)
        except Exception as exc:
            if json_mode and "response_format" in str(exc):
                params.pop("response_format", None)
                completion = self._client.chat.completions.create(**params)
            else:
                raise

        choice = completion.choices[0]
        usage = completion.usage
        finish_reason = getattr(choice, "finish_reason", None)

        return LLMResponse(
            text=choice.message.content or "",
            token_usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                provider="groq",
            ),
            provider="groq",
            model=GROK_MODEL,
            finish_reason=finish_reason,
        )

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> Iterator[StreamChunk]:
        self._ensure_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        stream = self._client.chat.completions.create(
            model=GROK_MODEL,
            messages=messages,
            stream=True,
            max_tokens=min(
                max_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
                GROQ_MAX_OUTPUT_TOKENS,
            ),
        )
        for chunk in stream:
            content = (
                chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else ""
            )
            if content:
                yield StreamChunk(content=content, finished=False)
        yield StreamChunk(content="", finished=True)


class OllamaProvider:
    """The single active provider: an OpenAI-compatible server (Ollama).

    Base URL, model and key come from settings (LLM_BASE_URL / LLM_MODEL /
    LLM_API_KEY) and are read when the client is built, so restarting the
    process after a tunnel change is enough — no code edits. The key is a
    placeholder; the endpoint does not authenticate.
    """

    def __init__(
        self, client: Any = None, base_url: str | None = None, model: str | None = None
    ) -> None:
        self._client = client
        self._base_url = base_url
        self._model = model
        self._initialized = False

    @property
    def model(self) -> str:
        return self._model or settings.llm_model

    def _ensure_client(self) -> None:
        if not self._initialized:
            from openai import OpenAI

            if self._client is None:
                base_url = (self._base_url or settings.llm_base_url or "").strip().rstrip("/")
                if not base_url:
                    raise LLMProviderError("ollama", "LLM_BASE_URL is not configured.")
                self._client = OpenAI(
                    api_key=settings.llm_api_key or "ollama",
                    base_url=base_url,
                    timeout=PROVIDER_TIMEOUT_SECONDS,
                    max_retries=0,
                )
            self._initialized = True

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        json_mode: bool = False,
        timeout: float | None = None,
    ) -> LLMResponse:
        self._ensure_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        params: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
        }
        if json_mode:
            params["response_format"] = {"type": "json_object"}

        # A per-request timeout (e.g. heavy planning) overrides the client
        # default without changing intake/video/other Ollama calls.
        client = self._client if timeout is None else self._client.with_options(timeout=timeout)

        try:
            completion = client.chat.completions.create(**params)
        except Exception as exc:
            # Older/smaller local models may reject response_format; retry plain.
            if json_mode and "response_format" in str(exc):
                params.pop("response_format", None)
                completion = client.chat.completions.create(**params)
            else:
                raise

        choice = completion.choices[0]
        usage = completion.usage
        return LLMResponse(
            text=choice.message.content or "",
            token_usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                provider="ollama",
            ),
            provider="ollama",
            model=self.model,
            finish_reason=getattr(choice, "finish_reason", None),
        )

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> Iterator[StreamChunk]:
        self._ensure_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        stream = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            max_tokens=max_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
        )
        for chunk in stream:
            content = (
                chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else ""
            )
            if content:
                yield StreamChunk(content=content, finished=False)
        yield StreamChunk(content="", finished=True)


def _call_provider_generate(
    provider_instance: Any,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    json_mode: bool,
    timeout: float | None = None,
) -> LLMResponse:
    # Pass `timeout` only to a provider that names it explicitly (the local
    # Ollama provider). Hosted providers never receive it and keep their
    # own timeout behaviour untouched.
    extra: dict[str, Any] = {}
    try:
        params = inspect.signature(provider_instance.generate).parameters
        if timeout is not None and "timeout" in params:
            extra["timeout"] = timeout
        if "json_mode" in params or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        ):
            return provider_instance.generate(
                system_prompt,
                user_prompt,
                max_tokens,
                json_mode=json_mode,
                **extra,
            )
    except (ValueError, TypeError):
        pass
    try:
        return provider_instance.generate(
            system_prompt,
            user_prompt,
            max_tokens,
            json_mode=json_mode,
            **extra,
        )
    except TypeError:
        try:
            return provider_instance.generate(system_prompt, user_prompt, max_tokens)
        except TypeError:
            return provider_instance.generate(system_prompt, user_prompt)


def _build_credential_chain(order: list[str]) -> list[tuple[str, Any, str]]:
    """Build a remote failover chain with ONE entry per configured API key.

    ``order`` lists provider tiers in priority order (e.g. groq → openrouter →
    gemini). Every configured key for a tier becomes its own chain entry, so a
    rate-limited key rolls over to the next key of the same provider before the
    chain drops to the next (lower-priority) tier. Tiers with no configured key
    are skipped. Entry labels are the base provider name only — never key
    material — so logs stay secret-safe.
    """
    builders: dict[str, tuple[Any, Any, str]] = {
        "groq": (settings.get_groq_keys, lambda k: GroqProvider(api_key=k), GROK_MODEL),
        "openrouter": (
            settings.get_openrouter_keys,
            lambda k: OpenRouterProvider(api_key=k),
            settings.openrouter_model,
        ),
        "gemini": (settings.get_gemini_keys, lambda k: GeminiProvider(api_key=k), GEMINI_MODEL),
    }
    chain: list[tuple[str, Any, str]] = []
    for name in order:
        get_keys, make, model = builders[name]
        for key in get_keys():
            chain.append((name, make(key), model))
    return chain


def _validate_structured_response(
    response: LLMResponse,
    request: LLMRequest,
    provider_name: str,
) -> None:
    """Validate JSON format and schema for json_mode requests."""
    # 1. Truncation check
    finish = str(response.finish_reason).lower() if response.finish_reason else ""
    if finish in {"length", "max_tokens", "2"} or "length" in finish or "max_tokens" in finish:
        raise LLMProviderError(
            provider_name,
            f"Response was truncated due to token limit (finish_reason={response.finish_reason}).",
        )

    # 2. JSON parsing
    try:
        parsed = parse_json_object(response.text)
    except Exception as exc:
        snippet = response.text[:200].replace("\n", " ")
        raise LLMProviderError(
            provider_name,
            f"The LLM response did not contain a valid JSON object: {exc}. Snippet: {snippet!r}",
        ) from exc

    # 3. Schema validation if output_schema is provided
    if request.output_schema is not None:
        try:
            request.output_schema.model_validate(parsed)
        except Exception as exc:
            raise LLMProviderError(
                provider_name,
                f"The LLM response does not match the required schema: {exc}",
            ) from exc


class LLMService:
    def __init__(
        self,
        gemini: Any = None,
        openrouter: Any = None,
        groq: Any = None,
        primary: Any = None,  # Legacy test support
        fallback: Any = None,  # Legacy test support
        rotate_providers: bool | None = None,
    ) -> None:
        has_injected_provider = any(
            provider is not None for provider in (gemini, openrouter, groq, primary, fallback)
        )
        self._rotate_providers = (
            not has_injected_provider if rotate_providers is None else rotate_providers
        )
        # Name of the provider that served the most recent successful generate()
        # — lets a planning lane report which provider actually answered and
        # whether a fallback was used.
        self._last_provider: str | None = None
        self._ollama = None
        self._gemini = None
        self._openrouter = None
        self._groq = None

        if has_injected_provider:
            # Explicitly injected providers (tests / callers) are honoured as-is.
            self._gemini = gemini or fallback or GeminiProvider()
            self._openrouter = openrouter or OpenRouterProvider()
            self._groq = groq or primary or GroqProvider()
            self._chain = [
                ("gemini", self._gemini, GEMINI_MODEL),
                ("openrouter", self._openrouter, settings.openrouter_model),
                ("groq", self._groq, GROK_MODEL),
            ]
        elif _remote_mode():
            # Remote-only (default): the ordinary service routes to the hosted
            # provider chain (groq -> openrouter -> gemini, every configured key),
            # with per-call key rotation and roll-over. No Ollama is constructed
            # or wired in, so no default request path can require it.
            self._chain = _build_credential_chain(["groq", "openrouter", "gemini"])
        else:
            # Legacy (LLM_MODE=ollama): single active provider, the
            # OpenAI-compatible endpoint at LLM_BASE_URL. The hosted providers
            # remain importable/configurable but are not wired into the chain.
            self._ollama = OllamaProvider()
            self._chain = [("ollama", self._ollama, settings.llm_model)]

    def is_local_ollama(self) -> bool:
        """True when the only active provider is the local Ollama endpoint.

        The single truthful signal for provider-specific planning policy
        (concurrency of 1, longer timeout, no timeout-retry).
        """
        return len(self._chain) == 1 and self._chain[0][0] == "ollama"

    def has_ollama_provider(self) -> bool:
        """True when an Ollama provider is anywhere in this service's chain.

        Used so a planning lane whose primary is Ollama (with a remote
        fallback appended) still gets the long planning timeout applied to
        its Ollama leg.
        """
        return any(name == "ollama" for name, _, _ in self._chain)

    @classmethod
    def planning_ollama_lane(cls, base_url: str, model: str) -> LLMService:
        """A planning lane whose primary is a specific Ollama endpoint, with the
        canonical remote providers appended as sequential fallback.

        On an Ollama timeout the existing policy (no same-Ollama retry) applies
        and the service advances to the remote chain — never to another lane's
        Ollama GPU.
        """
        if _remote_mode():
            # Remote-only mode never contacts an Ollama GPU: the planning lane is
            # the canonical remote chain, so callers keep working unchanged even
            # when PLANNING_OLLAMA_A/B are configured but unreachable.
            return cls.planning_remote_lane()
        svc = cls(rotate_providers=False)  # builds the default single-Ollama chain
        ollama = OllamaProvider(base_url=base_url, model=model)
        svc._ollama = ollama
        # Ollama stays the deterministic first choice; the remote tiers
        # (groq → openrouter → gemini, all keys) are roll-over fallbacks only.
        svc._chain = [("ollama", ollama, model)] + _build_credential_chain(
            ["groq", "openrouter", "gemini"]
        )
        return svc

    @classmethod
    def planning_remote_lane(cls) -> LLMService:
        """A planning lane on the canonical remote provider chain only.

        Tiered, multi-key roll-over: groq → openrouter → gemini (gemini least
        priority), every configured key of each provider included, rotating so
        consecutive calls spread across credentials to avoid TPM limits.
        """
        svc = cls.__new__(cls)
        svc._rotate_providers = True
        svc._last_provider = None
        svc._ollama = None
        svc._gemini = None
        svc._openrouter = None
        svc._groq = None
        svc._chain = _build_credential_chain(["groq", "openrouter", "gemini"])
        return svc

    @classmethod
    def intake_remote_chain(cls) -> LLMService:
        """Dedicated intake provider chain: groq → openrouter → gemini.

        Intake is remote-only and must never resolve to any Ollama endpoint
        (global or planning-specific). Providers are tried in tier priority
        groq → openrouter → gemini (gemini least priority), with every
        configured key of each provider included as roll-over. Rotation spreads
        consecutive calls across credentials to avoid TPM limits; the tier order
        (and therefore structured-output failover order) stays deterministic.
        No planning timeout, no planning semaphore, no Ollama.
        """
        svc = cls.__new__(cls)
        svc._rotate_providers = True  # spread across credentials to avoid TPM
        svc._last_provider = None
        svc._ollama = None  # explicitly excluded
        svc._gemini = None
        svc._openrouter = None
        svc._groq = None
        svc._chain = _build_credential_chain(["groq", "openrouter", "gemini"])
        logger.info(
            "Intake LLM provider chain (roll-over): %s",
            " -> ".join(name for name, _, _ in svc._chain) or "(none configured)",
        )
        return svc

    @classmethod
    def video_remote_lane(cls) -> LLMService:
        """A remote-only provider chain for video script/director generation.

        Video script generation must never touch the local Ollama endpoint
        (single GPU, 60s timeout that this generation was overrunning). Providers
        are tried gemini → openrouter → groq, with every configured key of each
        provider included as roll-over. Rotation spreads consecutive calls across
        credentials to avoid TPM/rate limits; the tier order (and therefore the
        failover order) stays deterministic. No Ollama, and the global default
        LLMService (single-Ollama) and planning/intake lanes are unchanged.
        """
        svc = cls.__new__(cls)
        svc._rotate_providers = True  # spread across credentials to avoid TPM
        svc._last_provider = None
        svc._ollama = None  # explicitly excluded
        svc._gemini = None
        svc._openrouter = None
        svc._groq = None
        svc._chain = _build_credential_chain(["gemini", "openrouter", "groq"])
        logger.info(
            "Video script LLM provider chain (roll-over): %s",
            " -> ".join(name for name, _, _ in svc._chain) or "(none configured)",
        )
        return svc

    def _ordered_chain(self) -> list[tuple[str, Any, str]]:
        """Order the chain for one call: tier priority + intra-tier key rotation.

        Provider tiers keep their configured priority order (e.g. groq before
        openrouter before gemini — gemini least priority), but the keys WITHIN a
        tier are rotated per call so consecutive calls start on a different
        credential and spread token usage to avoid TPM limits. Credentials in
        cooldown (rate-limited) are skipped, rolling over to the next key.
        """
        if not self._rotate_providers:
            return list(self._chain)

        from collections import OrderedDict

        groups: OrderedDict[str, list[tuple[str, Any, str]]] = OrderedDict()
        for entry in self._chain:
            groups.setdefault(entry[0], []).append(entry)

        global _provider_rotation_index
        with _provider_rotation_lock:
            idx = _provider_rotation_index
            _provider_rotation_index += 1
            now = time.monotonic()
            ordered: list[tuple[str, Any, str]] = []
            for entries in groups.values():
                if len(entries) > 1:
                    offset = idx % len(entries)
                    entries = entries[offset:] + entries[:offset]
                ordered.extend(entries)
            available = [
                entry
                for entry in ordered
                if _provider_unavailable_until.get(id(entry[1]), 0.0) <= now
            ]
            skipped = [entry[0] for entry in ordered if entry not in available]

        if skipped:
            logger.info("LLM credentials skipped during cooldown: %s", ", ".join(skipped))
        # If every credential is cooling down, probe in order so recovery
        # remains possible instead of failing without making an attempt.
        return available or ordered

    def _mark_provider_failure(
        self, provider_instance: Any, provider_name: str, exc: Exception
    ) -> None:
        if not self._rotate_providers:
            return
        cooldown_seconds = 60.0
        if _is_rate_limit_error(exc):
            cooldown_seconds = 300.0
            msg = str(exc).lower()
            import contextlib
            import re

            m = re.search(r"(?:try again in|retry after)\s*~?([0-9.]+)\s*s", msg)
            if m:
                with contextlib.suppress(ValueError):
                    cooldown_seconds = min(float(m.group(1)) + 1.0, 300.0)

        # Cooldown is per-credential (id of the provider instance), so a
        # rate-limited key rolls over to its sibling key rather than disabling
        # the whole provider tier.
        with _provider_rotation_lock:
            _provider_unavailable_until[id(provider_instance)] = time.monotonic() + cooldown_seconds
        logger.info(
            "LLM credential cooldown started: %s for %.0fs",
            provider_name,
            cooldown_seconds,
        )

    def _mark_provider_success(self, provider_instance: Any, provider_name: str) -> None:
        if not self._rotate_providers:
            return
        with _provider_rotation_lock:
            _provider_unavailable_until.pop(id(provider_instance), None)

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

        last_error = None
        chain = self._ordered_chain()
        output_token_budget = request.max_tokens or DEFAULT_MAX_OUTPUT_TOKENS
        estimated_input_tokens = max(1, (len(system_prompt) + len(request.user_prompt) + 3) // 4)
        logger.warning(
            "LLM provider order for this request: %s",
            " -> ".join(provider_name for provider_name, _, _ in chain),
        )
        # A timed-out local (Ollama) generation may still hold the single GPU,
        # so its request is not resent; hosted providers keep normal retries.
        for provider_name, provider_instance, model_name in chain:
            provider_start = time.perf_counter()
            retry_on_timeout = provider_name != "ollama"
            call_timeout = request.timeout if provider_name == "ollama" else None
            logger.warning(
                "LLM provider attempt started: %s (%s), estimated input=%d tokens, max output=%d tokens",
                provider_name,
                model_name,
                estimated_input_tokens,
                output_token_budget,
            )
            try:
                # _retry_with_backoff will raise if it exhausts retries or hits auth errors
                response = _retry_with_backoff(
                    _call_provider_generate,
                    provider_instance,
                    system_prompt,
                    request.user_prompt,
                    output_token_budget,
                    request.json_mode,
                    call_timeout,
                    retry_on_timeout=retry_on_timeout,
                )

                if request.json_mode:
                    try:
                        _validate_structured_response(response, request, provider_name)
                    except LLMProviderError as val_err:
                        if "truncated" in str(val_err).lower():
                            logger.warning(
                                "LLM provider %s output was truncated; attempting concise repair retry: %s",
                                provider_name,
                                val_err,
                            )
                            repair_prompt = (
                                f"{request.user_prompt}\n\n"
                                "Return only valid JSON matching the required schema. Be concise. Do not include commentary or markdown."
                            )
                        else:
                            logger.warning(
                                "LLM provider %s returned invalid structured output; attempting single repair retry: %s",
                                provider_name,
                                val_err,
                            )
                            repair_prompt = (
                                f"{request.user_prompt}\n\n"
                                "Return only valid JSON matching the required schema. No markdown, commentary, or code fences."
                            )

                        repair_response = _retry_with_backoff(
                            _call_provider_generate,
                            provider_instance,
                            system_prompt,
                            repair_prompt,
                            output_token_budget,
                            request.json_mode,
                            call_timeout,
                            retry_on_timeout=retry_on_timeout,
                        )
                        _validate_structured_response(repair_response, request, provider_name)
                        logger.warning(
                            "LLM provider %s repair retry succeeded in %.1fs",
                            provider_name,
                            time.perf_counter() - provider_start,
                        )
                        response = repair_response

                logger.warning(
                    "LLM provider attempt succeeded: %s in %.1fs",
                    provider_name,
                    time.perf_counter() - provider_start,
                )
                self._last_provider = provider_name
                self._mark_provider_success(provider_instance, provider_name)
                self._record_telemetry(
                    request, system_prompt, response, start, provider_name, model_name, None
                )
                return response
            except Exception as exc:
                if self._is_auth_error(exc) or "missing API key" in str(exc):
                    logger.info(
                        "LLM provider skipped: %s after %.1fs (auth/missing key): %s",
                        provider_name,
                        time.perf_counter() - provider_start,
                        exc,
                    )
                else:
                    logger.warning(
                        "LLM provider attempt failed: %s after %.1fs: %s",
                        provider_name,
                        time.perf_counter() - provider_start,
                        exc,
                    )

                self._mark_provider_failure(provider_instance, provider_name, exc)
                last_error = exc
                continue

        # If all fail
        error_msg = f"All LLM providers failed. Last error: {last_error}"
        self._record_telemetry(request, system_prompt, None, start, "unknown", "unknown", error_msg)
        raise LLMServiceError(error_msg) from last_error

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
        """Attach this call to the active workflow trace, if any."""
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

        last_error = None
        for provider_name, provider_instance, _ in self._ordered_chain():
            try:
                # Test connection / instantiate client
                # If this yields successfully, we break the failover and stream it
                return provider_instance.generate_stream(
                    system_prompt,
                    request.user_prompt,
                    request.max_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
                )
            except Exception as exc:
                logger.warning("Provider %s stream init failed: %s", provider_name, exc)
                last_error = exc
                continue

        raise LLMServiceError(f"All LLM providers failed. Last error: {last_error}")
