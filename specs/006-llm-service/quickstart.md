# Quickstart: LLM Integration Service

## New Files to Create

| Path | Purpose |
|------|---------|
| `backend/src/models/llm.py` | `LLMResponse`, `TokenUsage`, `StreamChunk` dataclasses + Pydantic schemas |
| `backend/src/services/llm_service.py` | `LLMService` (unified interface) + internal `OpenAIProvider`, `GeminiProvider` |
| `backend/src/config/prompts.py` | `PROMPT_TEMPLATES` dict + `render_template()` / `register_template()` |
| `backend/tests/unit/test_llm_models.py` | Tests for model dataclasses and Pydantic schemas |
| `backend/tests/unit/test_llm_service.py` | Tests for `LLMService` with mocked providers |
| `backend/tests/unit/test_prompts.py` | Tests for template rendering |
| `backend/tests/integration/test_llm_api.py` | API endpoint tests (if API routes are added) |

## Existing Files to Modify

| Path | Change |
|------|--------|
| `backend/src/services/llm.py` | No change — this file serves guest search; new `llm_service.py` is separate |
| `backend/tests/unit/test_llm_service.py` | Rename to `test_llm_service_old.py` or extend (existing tests test guest-search LLM) |

## Implementation Order

| Step | File | Description |
|------|------|-------------|
| 1 | `test_llm_models.py` | Test `TokenUsage`, `LLMResponse`, `StreamChunk`, `LLMRequest` data models |
| 2 | `models/llm.py` | Implement the dataclasses and Pydantic schemas |
| 3 | `test_prompts.py` | Test `render_template` and `register_template` |
| 4 | `config/prompts.py` | Implement `PROMPT_TEMPLATES`, `render_template()`, `register_template()` |
| 5 | `test_llm_service.py` | Test `LLMService.generate()`, streaming, retry, fallback, error cases |
| 6 | `services/llm_service.py` | Implement `LLMService` with `OpenAIProvider` and `GeminiProvider` |

## Key Design Rules

1. **Sync only** — all services are synchronous (no async LLM calls)
2. **Lazy init** — providers created on first call, not in `__init__`
3. **Retry decorator** — follow `SupabaseService._retry` pattern (3 attempts, exponential backoff, max 3)
4. **Fallback** — primary exhausted → fallback one attempt → raise if both fail
5. **No streaming fallback** — per spec, streaming errors propagate immediately
6. **Template variables** — `{missing_var}` left as-is (don't crash, don't silently omit)
7. **Token usage** — provider-native counts, clearly labeled with provider name
8. **No ABC** — internal providers duck-type; no abstract base class

## Testing Commands

```bash
# Run all LLM-related tests
uv run pytest backend/tests/unit/test_llm_models.py backend/tests/unit/test_prompts.py backend/tests/unit/test_llm_service.py -v

# With coverage
uv run pytest --cov=src/services/llm_service --cov=src/models/llm --cov=src/config/prompts

# Full suite
uv run pytest
```
