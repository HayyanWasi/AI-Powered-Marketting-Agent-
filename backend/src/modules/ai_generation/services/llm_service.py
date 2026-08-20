"""LLM service for AI Generation Engine."""

from datetime import datetime
from typing import Any

from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI

from src.config.settings import settings

from ..constants import SeverityLevel


class ValidationError:
    """Individual validation error."""

    def __init__(
        self,
        code: str,
        message: str,
        severity: str,
        field: str | None = None,
        suggested_fix: str | None = None,
    ):
        self.code = code
        self.message = message
        self.severity = severity
        self.field = field
        self.suggested_fix = suggested_fix

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "field": self.field,
            "suggested_fix": self.suggested_fix,
        }


class ValidationWarning:
    """Individual validation warning."""

    def __init__(self, code: str, message: str, field: str | None = None):
        self.code = code
        self.message = message
        self.field = field

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
        }


class LLMGenerationError(Exception):
    """Raised when an LLM call fails and the caller opted out of silent fallback."""


def _trim_prompt(prompt: str, max_chars: int = 10000) -> str:
    """Trim large prompts to fit safely within LLM TPM rate limits."""
    if not prompt or len(prompt) <= max_chars:
        return prompt
    head_len = int(max_chars * 0.6)
    tail_len = max_chars - head_len - 80
    return (
        prompt[:head_len]
        + "\n\n... [middle context truncated to fit model token limits] ...\n\n"
        + prompt[-tail_len:]
    )


class LLMService:
    """Service for LLM-powered text generation using Groq."""

    DEFAULT_MODEL = "openai/gpt-oss-120b"
    FAST_MODEL = "openai/gpt-oss-20b"
    REASONING_MODEL = "openai/gpt-oss-120b"

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        provider: str | None = None,
    ):


        self.provider = (provider or "groq").lower()
        if self.provider == "openrouter":
            self.api_key = api_key or getattr(settings, "openrouter_api_key", "") or getattr(settings, "grok_api_key", "")
            self.base_url = "https://openrouter.ai/api/v1"
            self.model = model or getattr(settings, "openrouter_model", "google/gemma-2-9b-it:free")
        elif self.provider == "gemini":
            self.api_key = api_key or getattr(settings, "google_api_key", "")
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
            self.model = model or "gemini-3.5-flash"
        else:
            self.api_key = api_key or settings.grok_api_key
            self.base_url = "https://api.groq.com/openai/v1"
            self.model = model or self.DEFAULT_MODEL


        if self.api_key:
            self.client = wrap_openai(AsyncOpenAI(api_key=self.api_key, base_url=self.base_url))
        else:
            self.client = None


    from langsmith import traceable

    @traceable(name="llm_generate_json")
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        trace_id: str | None = None,
        workflow_id: str | None = None,
        prompt_name: str = "general_generation",
        raise_on_error: bool = False,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Generate JSON output using the LLM.

        Args:
            raise_on_error: Raise LLMGenerationError instead of returning {}.
                Callers running inside the workflow pipeline should set this so
                the retry wrapper sees the failure.
            temperature: Sampling temperature (0.0 for deterministic, 0.7 default).
        """
        import json
        import logging
        import time
        import uuid

        from src.api.dependencies import get_operations_service

        if not self.client:
            if raise_on_error:
                raise LLMGenerationError("No Groq API key configured.")
            logging.getLogger(__name__).warning("No Groq API key found. Returning empty dict.")
            return {}

        operations = get_operations_service()
        start_time = time.perf_counter()
        status = "success"
        error_msg = None

        # Truncate prompt to prevent Groq 413 / 6000 TPM limit overflow
        safe_user_prompt = _trim_prompt(user_prompt, max_chars=10000)
        input_tokens = len(system_prompt.split()) + len(safe_user_prompt.split())  # Estimate
        output_tokens = 0

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                        + "\n\nProvide your response ONLY as valid JSON. Do not include markdown formatting or explanations.",
                    },
                    {"role": "user", "content": safe_user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=2000,
            )


            result_text = response.choices[0].message.content
            logging.getLogger(__name__).info("[LLM CALL SUCCESS] Provider: %s | Model: %s", self.provider, self.model)
            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
            else:
                output_tokens = len(result_text.split())

            import re
            clean_text = re.sub(r"<think>[\s\S]*?</think>", "", result_text)
            fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", clean_text)
            if fenced:
                clean_text = fenced.group(1)
            start = clean_text.find("{")
            end = clean_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(clean_text[start : end + 1])
            return json.loads(clean_text)
        except Exception as e:
            # Tier 2 Failover: OpenRouter (Gemini / Gemma free models on OpenRouter)
            openrouter_key = getattr(settings, "openrouter_api_key", "") or getattr(settings, "grok_api_key", "") or getattr(settings, "google_api_key", "")
            if openrouter_key:
                openrouter_model = getattr(settings, "openrouter_model", "google/gemma-2-9b-it:free")
                logging.getLogger(__name__).warning(
                    "[LLM FAILOVER TIER 2] Primary LLM (%s:%s) failed (%s). Retrying with OpenRouter (%s)...",
                    self.provider, self.model, e, openrouter_model
                )
                try:
                    or_client = wrap_openai(AsyncOpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1"))
                    or_resp = await or_client.chat.completions.create(
                        model=openrouter_model,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt
                                + "\n\nProvide your response ONLY as valid JSON. Do not include markdown formatting or explanations.",
                            },
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.7,
                        max_tokens=2000,
                    )
                    result_text = or_resp.choices[0].message.content
                    logging.getLogger(__name__).info("[LLM FAILOVER SUCCESS] Tier 2 OpenRouter (%s) succeeded!", openrouter_model)
                    return json.loads(result_text)
                except Exception as or_err:
                    logging.getLogger(__name__).warning("[LLM FAILOVER TIER 2 FAILED] OpenRouter error: %s", or_err)

            # Tier 3 Failover: Groq (qwen/qwen3.6-27b)
            groq_key = getattr(settings, "grok_api_key", "")
            if groq_key:
                logging.getLogger(__name__).warning(
                    "[LLM FAILOVER TIER 3] Retrying with Groq (qwen/qwen3.6-27b)..."
                )
                try:
                    groq_client = wrap_openai(AsyncOpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1"))
                    groq_resp = await groq_client.chat.completions.create(
                        model="qwen/qwen3.6-27b",
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt
                                + "\n\nProvide your response ONLY as valid JSON. Do not include markdown formatting or explanations.",
                            },
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.7,
                        max_tokens=2000,
                    )
                    result_text = groq_resp.choices[0].message.content
                    logging.getLogger(__name__).info("[LLM FAILOVER SUCCESS] Tier 3 Groq (qwen/qwen3.6-27b) succeeded!")
                    return json.loads(result_text)
                except Exception as groq_err:
                    logging.getLogger(__name__).error("[LLM FAILOVER TIER 3 FAILED] Groq error: %s", groq_err)


            status = "error"
            error_msg = str(e)
            logging.getLogger(__name__).error(f"LLM Generation failed on provider={self.provider}: {e}")
            if raise_on_error:
                raise LLMGenerationError(str(e)) from e
            return {}

        finally:
            latency = int((time.perf_counter() - start_time) * 1000)
            # Fall back to the ambient workflow trace when the caller did not
            # pass one explicitly.
            if not (trace_id and workflow_id):
                from src.modules.operations.context import get_execution_context

                ctx = get_execution_context()
                if ctx:
                    trace_id, workflow_id = ctx
            if trace_id and workflow_id:
                try:
                    await operations.record_ai_request(
                        trace_id=uuid.UUID(trace_id) if isinstance(trace_id, str) else trace_id,
                        workflow_id=workflow_id,
                        prompt_version_id=operations.register_or_get_prompt_version(
                            name=prompt_name,
                            template=system_prompt,
                        ),
                        prompt_name=prompt_name,
                        model_name="groq",
                        model_version=self.model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        latency_ms=latency,
                        status=status,
                        error_message=error_msg,
                    )
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Failed to record AI telemetry: {e}")

    from langsmith import traceable

    @traceable(name="validate_strategy_content")
    def validate_strategy_content(
        self,
        strategy: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate strategy content for consistency.

        Args:
            strategy: Strategy to validate

        Returns:
            ValidationArtifact: Validation results
        """
        errors = []
        warnings = []
        compliance_scores = {}

        # Check if strategy has all required components
        required_components = [
            "audience_strategy",
            "messaging_strategy",
            "platform_strategy",
            "seo_strategy",
            "campaign_strategy",
        ]

        for component in required_components:
            if not strategy.get(component):
                errors.append(
                    ValidationError(
                        code="MISSING_STRATEGY_COMPONENT",
                        message=f"Missing required strategy component: {component}",
                        severity=SeverityLevel.ERROR,
                        field=f"strategy.{component}",
                    )
                )

        # Check strategy consistency
        if strategy.get("campaign_strategy", {}).get("goals"):
            goals = strategy["campaign_strategy"]["goals"]
            if isinstance(goals, str) and len(goals) < 10:
                warnings.append(
                    ValidationWarning(
                        code="TOO_SHORT_GOALS",
                        message="Campaign goals appear too brief",
                        field="campaign_strategy.goals",
                    )
                )

        # Platform compatibility check
        platforms = strategy.get("platform_strategy", {}).get("platforms", [])
        if platforms:
            for platform in platforms:
                platform_info = (
                    strategy.get("platform_strategy", {}).get("adaptations", {}).get(platform)
                )
                if not platform_info:
                    warnings.append(
                        ValidationWarning(
                            code="MISSING_PLATFORM_ADAPTATION",
                            message=f"No specific adaptation found for platform: {platform}",
                            field="platform_strategy.adaptations",
                        )
                    )

        # Compliance scores
        present_components = sum(1 for component in required_components if strategy.get(component))
        compliance_scores["required_components"] = (
            present_components / len(required_components) if required_components else 0
        )

        is_valid = len(errors) == 0

        return {
            "id": f"validation_strategy_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "strategy",
            "artifact_id": strategy.get("id", "unknown"),
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Ensure all strategy components are populated",
                "Add platform-specific adaptations for better targeting",
                "Define measurable campaign goals",
            ],
            "validated_by": "LLMService",
        }
