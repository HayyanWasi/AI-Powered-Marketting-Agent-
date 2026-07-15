# Implementation Plan: Guest Information Retrieval

**Branch**: `005-guest-info-search` | **Date**: 2026-07-15 | **Spec**: `specs/005-guest-info-search/spec.md`
**Input**: Feature specification from `/specs/005-guest-info-search/spec.md`

## Summary

Automatically gather publicly available guest/speaker information via DuckDuckGo search to generate structured guest profiles for personalized social media campaign content. The system accepts a guest name (required) and company name (optional), searches DuckDuckGo for up to 7 results, analyzes the metadata (snippets, titles, URLs) via an LLM, and produces a structured GuestProfile. Profiles are ephemeral — stored in session cache only (24-hour TTL), never persisted to database.

## Technical Context

**Language/Version**: Python 3.10+ (project requires >=3.13 per pyproject.toml)  
**Primary Dependencies**: duckduckgo-search>=3.9.0 (already in pyproject.toml), openai/google-generativeai SDK (already installed), pydantic>=2.0.0, dataclasses (stdlib)  
**Storage**: Session cache only — Python dict with 24-hour TTL (existing `SessionCache` in `backend/src/cache/cache.py`). No database persistence for guest profiles.  
**Testing**: pytest with pytest-cov, pytest-asyncio (already configured). All DDGS/LLM calls MUST be mocked in tests.  
**Target Platform**: Linux server (VPS — DigitalOcean, AWS EC2, or Google Cloud Run)  
**Project Type**: Web (backend service within existing FastAPI project)  
**Performance Goals**: DDGS search timeout <=15 seconds (from settings), rate limiter 5s minimum between calls. LLM analysis should complete within 30 seconds. End-to-end profile generation target: <45 seconds.  
**Constraints**: No webpage content scraping — search result metadata only. Max 7 search results. Ephemeral — never persist to database. Retry with name-only if company+name yields <3 results. Confidence scale: High/Medium/Low. Manual fallback when profile cannot be generated.  
**Scale/Scope**: Backend service within existing FastAPI app. Single API endpoint for guest search + profile generation. No frontend changes needed — this is a backend service capability.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Test-First**: Tests will be written before implementation. All DDGS/LLM calls mocked. (Principle I) — PASS
- [x] **Clean Code**: Dataclasses for internal models + Pydantic for API I/O (existing pattern). Type hints on all functions. No print statements. (Principle II) — PASS
- [x] **KISS/DRY**: Simple linear pipeline: search → analyze → profile. No LangGraph, no vector embeddings, no RAG. Reuses existing `SessionCache` for ephemeral storage. (Principle III) — PASS
- [x] **Fail Gracefully**: Error handling for DDGS timeouts/rate limits. Manual fallback when profile unreliable. No raw error exposure. (Principle IV) — PASS
- [x] **Architecture**: Linear pipeline — custom Python orchestration (no LangGraph). Ephemeral guest data — session cache only (24h TTL). Env-only config via existing `Settings`. All external calls mocked in tests. (Principle V) — PASS
- [x] **Coverage**: >=80% code coverage target. Focus on critical paths: search orchestration, retry logic, LLM analysis, fallback behavior. (Principle VI) — PASS
- [x] **Stack**: Uses approved tech: FastAPI (existing), duckduckgo-search (already in pyproject.toml), openai/google-generativeai (already installed). (Stack) — PASS

**Result**: All gates pass. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/005-guest-info-search/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── __init__.py       # Re-export GuestProfile models
│   │   └── guest_profile.py  # NEW: GuestProfile + SearchResult + ConfidenceLevel models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── supabase.py       # Existing
│   │   ├── search.py         # NEW: GuestSearchService (DDGS wrapper)
│   │   └── llm.py            # NEW: LLMService for search metadata analysis
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── company.py    # Existing
│   │       └── guest.py      # NEW: Guest profile search + generation endpoint
│   ├── cache/
│   │   ├── __init__.py       # Existing
│   │   ├── cache.py          # Existing SessionCache
│   │   └── session.py        # Existing Session dataclass
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py       # Existing (DDGS timeout/rate limit already present)
│   ├── agents/
│   │   └── __init__.py       # Existing (empty)
│   └── main.py               # Existing (include new guest router)
└── tests/
    ├── __init__.py
    ├── conftest.py           # Add mock fixtures for DDGS + LLM
    ├── unit/
    │   ├── test_guest_profile_model.py  # NEW
    │   ├── test_search_service.py       # NEW
    │   └── test_llm_service.py          # NEW
    └── integration/
        └── test_guest_search_api.py     # NEW
```

**Structure Decision**: Web application (Option 2) — backend-only feature within existing FastAPI project. Follows existing patterns:
- New `GuestSearchService` in `services/search.py` (mirrors `SupabaseService` pattern)
- New `LLMService` in `services/llm.py` for structured profile extraction
- New `guest_profile.py` models (dual Pydantic + dataclass pattern, mirrors `guest.py`)
- New `guest.py` API route (mirrors `company.py` pattern)

## Complexity Tracking

> All gates pass — no complexity violations to justify.
