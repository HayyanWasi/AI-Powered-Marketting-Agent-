# Data Model: LLM Integration Service

**Feature**: 006-llm-service | **Date**: 2026-07-15

## Entity Overview

| Entity | Kind | Storage | Description |
|--------|------|---------|-------------|
| `LLMRequest` | Pydantic (request) | In-memory (transient) | Input to the LLM service |
| `LLMResponse` | Dataclass + Pydantic (response) | In-memory (transient) | Normalized output from any LLM provider |
| `TokenUsage` | Dataclass + Pydantic | In-memory (transient) | Token counts labeled by provider |
| `StreamChunk` | Dataclass | In-memory (transient) | Single streaming delta |
| `PromptTemplate` | Python dict (code) | `config/prompts.py` | Named prompt strings with `{var}` placeholders |

## Entity Definitions

### TokenUsage

**Internal (dataclass)**:
```python
@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    provider: str = ""  # "openai" or "gemini"

    def to_response(self) -> TokenUsageData: ...
```

**API (Pydantic)**:
```python
class TokenUsageData(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    provider: str = ""
```

### StreamChunk

**Internal only** (dataclass — not serialized to API):
```python
@dataclass
class StreamChunk:
    content: str
    finished: bool = False
```

### LLMResponse

**Internal (dataclass)**:
```python
@dataclass
class LLMResponse:
    text: str
    token_usage: TokenUsage
    provider: str  # "openai" or "gemini"
    model: str     # actual model used

    def to_response(self) -> LLMResponseData: ...
```

**API (Pydantic)**:
```python
class LLMResponseData(BaseModel):
    text: str
    token_usage: TokenUsageData
    provider: str
    model: str
```

### LLMRequest

**API input (Pydantic)**:
```python
class LLMRequest(BaseModel):
    system_prompt: str | None = None      # Inline system prompt (alternative to template)
    user_prompt: str                      # Required: the user message
    template_name: str | None = None      # Named template to use for system prompt
    template_variables: dict[str, str] = {}  # Variables for template rendering
    stream: bool = False                  # Request streaming mode
```

## Provider Interface (Internal)

Not a formal ABC — internal provider classes duck-type this shape:

```python
@dataclass
class ProviderResponse:
    text: str
    token_usage: TokenUsage

class SomeProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> ProviderResponse: ...
    def generate_stream(self, system_prompt: str, user_prompt: str) -> Iterator[StreamChunk]: ...
```

## Validation Rules

| Field | Rule |
|-------|------|
| `user_prompt` | Required, non-empty after stripping |
| `template_name` | Must exist in `PROMPT_TEMPLATES` dict; error if not found |
| `system_prompt` / `template_name` | Mutually exclusive — exactly one must be provided |
| `token_usage` | Provider-labeled; streaming accumulates deltas into final counts |

## Relationships

```
LLMRequest
  ├── uses optional template_name → PromptTemplate (in config/prompts.py)
  ├── or uses inline system_prompt
  └── produces LLMResponse (standard) or Iterator[StreamChunk] (streaming)

LLMResponse
  └── contains TokenUsage (labeled by provider name)

LLMService
  ├── delegates to OpenAIProvider (primary)
  └── delegates to GeminiProvider (fallback)
```
