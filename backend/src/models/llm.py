from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    provider: str = ""

    def to_response(self) -> "TokenUsageData":
        return TokenUsageData(
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.total_tokens,
            provider=self.provider,
        )


class TokenUsageData(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    provider: str = ""


@dataclass
class LLMResponse:
    text: str
    token_usage: TokenUsage
    provider: str
    model: str

    def to_response(self) -> "LLMResponseData":
        return LLMResponseData(
            text=self.text,
            token_usage=self.token_usage.to_response(),
            provider=self.provider,
            model=self.model,
        )


class LLMResponseData(BaseModel):
    text: str
    token_usage: TokenUsageData
    provider: str
    model: str


@dataclass
class StreamChunk:
    content: str
    finished: bool = False


class LLMRequest(BaseModel):
    system_prompt: str | None = None
    user_prompt: str
    template_name: str | None = None
    template_variables: dict[str, str] = Field(default_factory=dict)
    prompt_name: str | None = None
