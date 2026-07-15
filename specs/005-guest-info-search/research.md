# Research: Guest Information Retrieval

## 1. DuckDuckGo Search API (DDGS)

- **Decision**: Use `from duckduckgo_search import DDGS` (installed v8.1.1). Call `DDGS().text(keywords, max_results=7)` for search.
- **Return format**: `list[dict]` — each dict has `title` (Page Title), `href` (Source URL), `body` (Search Description/Snippet). These map exactly to FR-02 requirements.
- **Error handling**: Raises `DuckDuckGoSearchException` (base), `RatelimitException` (rate limit), `TimeoutException` (timeout). Must catch and handle gracefully per Constitution Principle IV.
- **Rate limiting**: 5-second minimum between calls (configured in settings as `ddgs_rate_limit_seconds`). Use `asyncio.sleep()` or time-based throttling.
- **Timeout**: 15-second timeout per call (configured as `ddgs_timeout_seconds`). Can be set via `DDGS(timeout=15)`.
- **Retry logic**: When company+name search yields <3 results, retry with name-only (FR-01). Use same pattern as existing SupabaseService retry.
- **max_results**: Set to 7 per spec (FR-02). The `text()` method accepts `max_results` parameter directly.
- **Alternatives considered**: None — `duckduckgo-search` is already in `pyproject.toml` and is the approved search provider in the constitution.

## 2. LLM Structured Output (Guest Profile Extraction)

- **Decision**: Use OpenAI GPT-4o with `client.chat.completions.parse()` and `response_format=<PydanticModel>` for structured profile extraction from search metadata.
- **Rationale**: The `parse()` method automatically converts a Pydantic model to JSON schema, sends it to the API, and returns a parsed instance. This guarantees valid structured output matching the GuestProfile schema without manual JSON parsing.
- **Prompt design**: Provide all 7 search results (title + body + href) as context. Instruct the LLM to extract: Full Name, Current Position, Organization, Professional Biography, Areas of Expertise, Confidence Level, Sources Used. The LLM should only use information present in the provided metadata — never invent or assume.
- **Confidence logic**: Let the LLM assess High/Medium/Low based on consistency across results, number of corroborating sources, and presence of conflicts. High = consistent across multiple results, Medium = some corroboration, Low = single source or conflicting.
- **Alternatives considered**: Manual JSON parsing (error-prone), Google Gemini (available but OpenAI has more mature structured output support).
- **Edge cases**: Empty fields when uncertain (FR-06), conflict resolution (FR-05), partial information (FR-04).

## 3. Service Architecture Pattern

- **Decision**: Create two new services following the existing `SupabaseService` pattern:
  - `GuestSearchService` in `services/search.py` — wraps DDGS calls, handles retry logic, rate limiting, timeout.
  - `LLMService` in `services/llm.py` — wraps OpenAI chat completions, handles structured profile extraction.
- **Both services should**: Accept optional client for DI (testability), have custom exception hierarchy, use `logging.getLogger(__name__)`, be instantiated as module-level singletons in route files.
- **Alternatives considered**: Single monolithic service (violates SRP), agent-based approach (premature — no agents exist yet).

## 4. Session Cache Integration

- **Decision**: GuestProfile is ephemeral — never persist to database. Store generated profiles in the existing `SessionCache` using `session_id` from an existing or new session. The profile exists only for the current campaign generation session (24-hour TTL).
- **FR-07 fallback**: If profile cannot be generated, return a response with `needs_manual_input=True` and empty fields for biography, position, and organization.
- **Alternatives considered**: Database persistence (violates Constitution Principle V — "Ephemeral Guest Data").

## 5. API Contract Design

- **Decision**: Single POST endpoint at `/api/guest/search` that accepts `GuestSearchRequest` (name required, company optional) and returns `GuestSearchResponse` (profile or manual input request).
- **Pattern**: Follows existing `company.py` route pattern — `APIRouter(prefix="/api/guest", tags=["guest"])`.
- **Session handling**: Create a new session (via `SessionCache`) or use provided session_id in the request to associate the profile with a campaign session.
