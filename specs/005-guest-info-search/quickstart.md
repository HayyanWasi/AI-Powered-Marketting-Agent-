# Quickstart: Guest Information Retrieval

## Dependencies

Already installed (no new dependencies needed):
- `duckduckgo-search>=3.9.0` (v8.1.1 installed)
- `openai>=1.0.0`
- `pydantic>=2.0.0`

## Files to Create

### 1. Models: `backend/src/models/guest_profile.py`

Define dual models (Pydantic + dataclass):
- `ConfidenceLevel` (StrEnum: HIGH, MEDIUM, LOW)
- `SearchResultData` (Pydantic) + `SearchResult` (dataclass)
- `GuestProfileData` (Pydantic) + `GuestProfile` (dataclass with `to_response()` method)
- `GuestSearchRequest` (Pydantic request body)
- `GuestSearchResponse` (Pydantic response)

### 2. Search Service: `backend/src/services/search.py`

`class GuestSearchService`:
- `__init__(self, ddgs: DDGS | None = None)` — optional DI for testability
- `search(self, guest_name: str, company_name: str | None = None) -> list[dict]` — DDGS wrapper with rate limiting, timeout, retry logic
- Internal: if company_name provided, search with both; if <3 results, retry with name-only

### 3. LLM Service: `backend/src/services/llm.py`

`class LLMService`:
- `__init__(self, client: OpenAI | None = None)` — optional DI
- `analyze_search_results(self, results: list[dict]) -> GuestProfileData` — uses `client.chat.completions.parse()` with `response_format=GuestProfileData`

### 4. API Route: `backend/src/api/routes/guest.py`

- `APIRouter(prefix="/api/guest", tags=["guest"])`
- `POST /search` — accepts `GuestSearchRequest`, returns `GuestSearchResponse`
- Module-level singleton: `search_service = GuestSearchService()`, `llm_service = LLMService()`
- Integrates with `SessionCache` (store profile in session if `session_id` provided)

### 5. Main App: `backend/src/main.py`

- Add `app.include_router(guest_router)`

## Tests

### Unit Tests
- `tests/unit/test_guest_profile_model.py` — model validation, edge cases
- `tests/unit/test_search_service.py` — DDGS mock, retry logic, rate limiting
- `tests/unit/test_llm_service.py` — LLM mock, structured output parsing

### Integration Tests
- `tests/integration/test_guest_search_api.py` — full endpoint test with mocks

### Test fixtures (add to `tests/conftest.py`)
- `mock_ddgs` — returns controlled search results
- `mock_llm` — returns controlled `GuestProfileData`

## Verification

```bash
uv run ruff check backend/src backend/tests
uv run mypy backend/src backend/tests
uv run pytest
```
