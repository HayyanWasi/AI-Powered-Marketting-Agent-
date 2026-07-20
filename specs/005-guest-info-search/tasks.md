---

description: "Task list for Guest Information Retrieval feature implementation"

---

# Tasks: Guest Information Retrieval

**Input**: Design documents from `/specs/005-guest-info-search/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks are included per the constitution's Test-First principle (Principle I) and listed in quickstart.md.

**Status**: All 18 tasks completed ✅

## User Story 1 — Search and Generate Guest Profile (P1)

**What was built:**

1. **Data Models** (`backend/src/models/guest_profile.py`) — `ConfidenceLevel` (HIGH/MEDIUM/LOW enum), `SearchResult` (dataclass + Pydantic), `GuestProfile` (dataclass with `to_response()` + Pydantic), `GuestSearchRequest` / `GuestSearchResponse` (Pydantic API schemas)

2. **Search Service** (`backend/src/services/search.py`) — `GuestSearchService` wrapping DuckDuckGo (`DDGS().text()`), 15s timeout, 5s rate limiting, auto-retry with name-only when company+name yields <3 results, custom `SearchError` exception

3. **LLM Service** (`backend/src/services/llm.py`) — `LLMService` using OpenAI structured outputs (`client.chat.completions.parse()` with `response_format=GuestProfileData`), system prompt enforcing metadata-only analysis, never-invent rule, conflict→confidence lowering, custom `LLMError` exception

4. **API Endpoint** (`backend/src/api/routes/guest.py`) — `POST /api/guest/search`, accepts `GuestSearchRequest` (name required, company optional), returns `GuestSearchResponse` (profile or `needs_manual_input: true`), maps service errors to HTTP 502, validation errors to 422

5. **Integration** (`backend/src/main.py`) — Guest router wired into the FastAPI app

6. **Tests** — 30 new tests across 4 files:
   - `test_guest_profile_model.py` (17 tests): model defaults, validation, serialization, `to_response()`, empty-name rejection
   - `test_search_service.py` (8 tests): happy path, company retry, no results, rate limiting, error propagation, empty-company skip
   - `test_llm_service.py` (5 tests): structured output parsing, empty results, partial profiles, LLM error handling
   - `test_guest_search_api.py` (7 tests): full endpoint via `TestClient`, all 5 acceptance scenarios + 502/422 error cases

---

## Phase 1: Setup

**Purpose**: Verify project state — all dependencies already installed.

- [X] T001 Verify environment: run `uv run python -c "from duckduckgo_search import DDGS; print('ok')"` and `uv run python -c "from openai import OpenAI; print('ok')"` to confirm deps are available

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models and test fixtures that block all user story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Create `ConfidenceLevel` enum (StrEnum with HIGH/MEDIUM/LOW) in `backend/src/models/guest_profile.py`
- [X] T003 [P] Create `SearchResult` dataclass + `SearchResultData` Pydantic model in `backend/src/models/guest_profile.py`
- [X] T004 [P] Create `GuestProfile` dataclass (with `to_response()` method) + `GuestProfileData` Pydantic response model in `backend/src/models/guest_profile.py`
- [X] T005 [P] Create `GuestSearchRequest` and `GuestSearchResponse` Pydantic models in `backend/src/models/guest_profile.py`
- [X] T006 Update `backend/src/models/__init__.py` to re-export `GuestProfile`, `GuestProfileData`, `SearchResult`, `SearchResultData`, `ConfidenceLevel`, `GuestSearchRequest`, `GuestSearchResponse`
- [X] T007 Add mock fixtures for DDGS and LLM to `backend/tests/conftest.py` — `mock_ddgs` fixture returning controlled search results, `mock_llm` fixture returning controlled `GuestProfileData`

**Checkpoint**: Foundation ready — models defined, fixtures available for testing.

---

## Phase 3: User Story 1 - Search and Generate Guest Profile (Priority: P1) 🎯 MVP

**Goal**: Marketing Organizer can submit a guest name (with optional company) and receive a structured profile generated from DuckDuckGo search metadata analyzed by an LLM.

**Independent Test**: Call `POST /api/guest/search` with `{"guest_name": "Ada Lovelace"}` and verify a structured profile is returned with populated fields and confidence level.

### Acceptance Criteria (from spec.md)

1. Valid guest name + optional company → structured profile with Full Name, Current Position, Organization, Professional Biography, Areas of Expertise, Confidence Level, Sources Used
2. Partial information → populate available fields, leave rest empty
3. Conflicting information → prefer consistent info, lower confidence when conflicts persist
4. No relevant results → `needs_manual_input: true`
5. Company+name yields <3 results → auto-retry with name-only

### Tests for User Story 1 ⚠️

- [X] T008 [P] [US1] Unit test for `GuestProfile` model validation and `to_response()` in `backend/tests/unit/test_guest_profile_model.py`
- [X] T009 [P] [US1] Unit test for `GuestSearchService.search()` — mock DDGS, test retry logic, rate limiting, timeout, edge cases in `backend/tests/unit/test_search_service.py`
- [X] T010 [P] [US1] Unit test for `LLMService.analyze_search_results()` — mock OpenAI, test structured output parsing, empty results handling in `backend/tests/unit/test_llm_service.py`
- [X] T011 [US1] Integration test for `POST /api/guest/search` — mock DDGS + LLM, test all 5 acceptance scenarios in `backend/tests/integration/test_guest_search_api.py`

### Implementation for User Story 1

- [X] T012 [US1] Implement `GuestSearchService` in `backend/src/services/search.py` — wraps `DDGS().text()` with `max_results=7`, 15s timeout, 5s rate limiting, retry logic (company+name → fallback to name-only when <3 results), custom exception hierarchy
- [X] T013 [US1] Implement `LLMService` in `backend/src/services/llm.py` — wraps `OpenAI().chat.completions.parse()` with `response_format=GuestProfileData`, builds system prompt from search result metadata, handles empty/partial results
- [X] T014 [US1] Implement API route `POST /api/guest/search` in `backend/src/api/routes/guest.py` — `APIRouter(prefix="/api/guest", tags=["guest"])`, module-level service singletons, accept `GuestSearchRequest`, return `GuestSearchResponse`, integrate with `SessionCache` when `session_id` provided, map exceptions to HTTP errors
- [X] T015 [US1] Wire up guest router in `backend/src/main.py` — add `from backend.src.api.routes.guest import router as guest_router` and `app.include_router(guest_router, prefix="/api")`

**Checkpoint**: User Story 1 fully functional. Run `uv run pytest` to confirm all tests pass.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Code quality, documentation, and verification.

- [X] T016 Run `uv run ruff check backend/src backend/tests` and fix any lint errors
- [X] T017 Run `uv run mypy backend/src backend/tests` and fix any type errors
- [X] T018 Run `uv run pytest --cov` and verify >=80% coverage; add missing tests if needed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user story work
- **User Story 1 (Phase 3)**: Depends on Foundational — models and fixtures must exist
- **Polish (Phase 4)**: Depends on User Story 1 being complete

### Within Phase 3 (User Story 1)

- Tests T008, T009, T010 are parallel — each tests different files
- T011 (integration test) depends on T008-T010 patterns but can be written independently
- T012 (SearchService) depends on models from Phase 2
- T013 (LLMService) depends on models from Phase 2
- T014 (API Route) depends on T012, T013
- T015 (main.py) depends on T014

### Parallel Opportunities

| Tasks | Can Run In Parallel | Reason |
|-------|-------------------|--------|
| T002, T003, T004, T005 | Yes | Different models, same file but independent sections |
| T008, T009, T010 | Yes | Different test files, different services |
| T012, T013 | Yes | Independent services (DDGS vs LLM) |

### Parallel Example: Phase 3

```text
# Launch models + tests together:
Task: "Create GuestSearchService in backend/src/services/search.py" (T012)
Task: "Create LLMService in backend/src/services/llm.py" (T013)

# Launch all unit tests together:
Task: "Test GuestProfile model in backend/tests/unit/test_guest_profile_model.py" (T008)
Task: "Test GuestSearchService in backend/tests/unit/test_search_service.py" (T009)
Task: "Test LLMService in backend/tests/unit/test_llm_service.py" (T010)
```

---

## Implementation Strategy

### MVP (Phase 1 + 2 + 3 Only)

1. Complete Phase 1: Verify deps
2. Complete Phase 2: Models + conftest
3. Implement tests (T008-T011) — confirm they fail before code
4. Implement SearchService (T012)
5. Implement LLMService (T013)
6. Implement API Route (T014) + main.py wiring (T015)
7. Run all tests — confirm all pass
8. Run lint + typecheck + coverage (Phase 4)

### Incremental Delivery Notes

- Since there is only one user story, the feature is delivered as a single increment.
- The API endpoint is the only public surface — once T015 is complete, the feature is usable.
- Total estimated tasks: 18

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Setup | T001 | ✅ Complete |
| Phase 2: Foundational (Models + Fixtures) | T002-T007 | ✅ Complete |
| Phase 3: US1 — Search & Generate Guest Profile | T008-T015 | ✅ Complete |
| Phase 4: Polish & Cross-Cutting | T016-T018 | ✅ Complete |
| **Total** | **18** | **100%** |
