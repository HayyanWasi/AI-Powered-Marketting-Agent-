# Research: LLM Integration Service

**Feature**: 006-llm-service | **Date**: 2026-07-15

## Provider SDK Analysis

### OpenAI SDK (`openai>=1.0.0`)

**Initialization**:
```python
from openai import OpenAI
client = OpenAI(api_key=settings.openai_api_key)
```

**Standard generation** (`client.chat.completions.create`):
```python
completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    stream=False,
)
text = completion.choices[0].message.content
usage = completion.usage  # prompt_tokens, completion_tokens, total_tokens
```

**Streaming** (`client.chat.completions.create(stream=True)`):
- Iterator of `ChatCompletionChunk` objects
- Each chunk: `chunk.choices[0].delta.content` (can be `None`)
- Final chunk may contain `usage`; accumulation needed for complete response
- Content deltas must be concatenated across chunks

**Error types**: `openai.APIConnectionError`, `openai.RateLimitError`, `openai.APIStatusError`

### Gemini SDK (`google-generativeai>=0.3.0`)

**Initialization**:
```python
import google.generativeai as genai
genai.configure(api_key=settings.google_api_key)
model = genai.GenerativeModel(
    'models/gemini-1.5-flash',
    system_instruction=system_prompt
)
```

**Standard generation**:
```python
response = model.generate_content(user_prompt, stream=False)
text = response.text
usage = response.usage_metadata  # prompt_token_count, candidates_token_count, total_token_count
```

**Streaming**:
- Iterator of `GenerateContentResponse` chunks
- Each chunk: `chunk.text` (available during iteration)
- `.usage_metadata` available after iteration completes
- `BlockedPromptException` for blocked content

**Built-in retry**: `google.api_core.retry.Retry` via `RequestOptions`

## Key Differences

| Aspect | OpenAI | Gemini |
|--------|--------|--------|
| System prompt | In messages array with `role: "system"` | `system_instruction` constructor param |
| User prompt | In messages array with `role: "user"` | Passed directly to `generate_content()` |
| Response text | `choices[0].message.content` | `.text` |
| Token usage | `.usage.prompt_tokens`, `.completion_tokens`, `.total_tokens` | `.usage_metadata.prompt_token_count`, `.candidates_token_count`, `.total_token_count` |
| Stream chunks | `.choices[0].delta.content` | `.text` |
| Final usage in stream | May appear in last chunk | Available after iteration |
| Model name | `"gpt-4o"` / `"gpt-4o-2024-08-06"` | `"models/gemini-1.5-flash"` |

## Normalization Strategy

A single `LLMService` class orchestrates both providers via internal provider wrappers:

```python
class LLMService:
    def __init__(self, openai_client=None, gemini_model=None):
        self._primary = OpenAIProvider(openai_client)
        self._fallback = GeminiProvider(gemini_model)
```

Each internal provider normalizes its SDK to a common return type (`LLMResponse`), hiding the SDK-specific response structures.

## Retry & Fallback Design

### Existing project pattern
`SupabaseService` uses `@_retry` decorator with `MAX_RETRIES=3`, exponential backoff of `2^attempt` seconds. Follow same pattern.

### Fallback flow
1. Primary (OpenAI): attempt → retry up to 3× (1s, 2s, 4s delays)
2. If all retries exhausted on transient errors → fallback to Gemini (single attempt)
3. If Gemini also fails → raise `LLMServiceError`
4. Authentication errors on primary → propagate immediately (no retry, no fallback)

### Streaming fallback
Per spec: streaming has no fallback. If streaming fails, error propagates to caller.

## Model Selection

- **OpenAI**: `"gpt-4o"` (use `"gpt-4o-2024-08-06"` for structured output compatibility, or `"gpt-4o"` for general use)
- **Gemini**: `"models/gemini-1.5-flash"` (fast, cost-effective fallback)

Configurable via constants/settings so model names can be adjusted without code changes.

## Template System Design

Named prompt templates stored in Python file (`config/prompts.py`):
```python
PROMPT_TEMPLATES: dict[str, str] = {
    "campaign_instagram": """You are an Instagram marketing expert...
    Tone: {company_tone}
    Guest: {guest_name}""",
    "campaign_linkedin": """...""",
}
```

Template rendering: simple `template.format(**variables)` — missing variables left as-is per spec.

## Token Tracking

Both SDKs return usage metadata natively. The unified response object maps provider-specific names to canonical fields:

| Canonical Field | OpenAI Source | Gemini Source |
|----------------|---------------|---------------|
| `prompt_tokens` | `usage.prompt_tokens` | `usage_metadata.prompt_token_count` |
| `completion_tokens` | `usage.completion_tokens` | `usage_metadata.candidates_token_count` |
| `total_tokens` | `usage.total_tokens` | `usage_metadata.total_token_count` |

## Streaming Contract Normalization

Both providers produce iterables of partial content. Normalize to a generator yielding `StreamChunk` objects:

```python
@dataclass
class StreamChunk:
    content: str          # Partial text delta
    finished: bool        # True for the final chunk
```

- **OpenAI streaming**: accumulate `delta.content` across chunks; track when `finish_reason` is not `None`
- **Gemini streaming**: each chunk has `.text`; final chunk accumulates full text

## Key Decisions

1. **Sync only** — All existing services are sync; no async LLM interface needed
2. **Internal provider classes** — Not exported; `LLMService` is the only public API
3. **Retry pattern** — Reuse `@_retry` decorator or inline retry logic matching SupabaseService pattern
4. **Lazy init** — Providers initialized on first use, not at construction time (deferred error per spec)
5. **No ABC/interface** — KISS: internal provider classes duck-type the same methods
