"""Data model contracts for LLM Integration Service.

These stubs define the exact types and method signatures.
Implementation must match these contracts exactly.
"""

from dataclasses import dataclass, field

from pydantic import BaseModel

# ─── Token Usage ────────────────────────────────────────────────────


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    provider: str = ""  # "openai" or "gemini"

    def to_response(self) -> "TokenUsageData": ...


class TokenUsageData(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    provider: str = ""


# ─── LLM Response ───────────────────────────────────────────────────


@dataclass
class LLMResponse:
    text: str
    token_usage: TokenUsage
    provider: str  # "openai" or "gemini"
    model: str  # actual model name used

    def to_response(self) -> "LLMResponseData": ...


class LLMResponseData(BaseModel):
    text: str
    token_usage: TokenUsageData
    provider: str
    model: str


# ─── Stream Chunk ───────────────────────────────────────────────────


@dataclass
class StreamChunk:
    content: str
    finished: bool = False


# ─── LLM Request ────────────────────────────────────────────────────


class LLMRequest(BaseModel):
    system_prompt: str | None = None  # inline system prompt
    user_prompt: str  # required user message
    template_name: str | None = None  # named template in prompts.py
    template_variables: dict[str, str] = field(default_factory=dict)
    stream: bool = False  # request streaming mode
