# AI-powered-marketing-agent Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-07-19

## Active Technologies
- Python 3.13 + supabase (Python SDK), fastapi, python-multipart, Pillow (PIL), pydantic, httpx (002-database-storage)
- Supabase PostgreSQL (company_profiles table) + Supabase Storage (public bucket for brand images) (002-database-storage)
- Python 3.10+ (project requires >=3.13) + Standard library only (uuid, threading, time, dataclasses) — no external packages (003-session-cache-system)
- In-memory (Python dict) — no database or persistence (003-session-cache-system)
- Python 3.10+ (project requires >=3.13) + pydantic (already in project), dataclasses (stdlib) (004-data-models-schemas)
- N/A — models define data shape, not storage (004-data-models-schemas)
- Python 3.10+ (project requires >=3.13 per pyproject.toml) + duckduckgo-search>=3.9.0 (already in pyproject.toml), openai/google-generativeai SDK (already installed), pydantic>=2.0.0, dataclasses (stdlib) (005-guest-info-search)
- Session cache only — Python dict with 24-hour TTL (existing `SessionCache` in `backend/src/cache/cache.py`). No database persistence for guest profiles. (005-guest-info-search)
- Python 3.13 (project requires >=3.13) + FastAPI, httpx (async HTTP), Pydantic v2, Pillow (PIL) for image validation, Supabase Python SDK (007-pollinations-brand-images)
- Supabase PostgreSQL (company_profiles table), Supabase Storage (brand reference images - public bucket) (007-pollinations-brand-images)
- Python 3.13+ (FastAPI) + FastAPI, supabase (Python SDK), httpx, Pillow (PIL), pydantic (009-company-profile-service)
- Python 3.13+ (FastAPI) + FastAPI, Supabase Python SDK, Pydantic v2, asyncpg (via Supabase), pytest, httpx (010-campaign-management)
- Supabase PostgreSQL (campaigns, campaign_configurations, campaign_history, campaign_assets tables) + Supabase Storage (for asset binaries if needed) (010-campaign-management)
- Python 3.13+ + langsmith>=0.1.0, opentelemetry-api>=1.20.0, opentelemetry-sdk>=1.20.0, opentelemetry-exporter-otlp-proto-http>=1.20.0, pydantic>=2.0.0, supabase>=2.0.0 (013-platform-operations)
- Supabase PostgreSQL (execution_history table), Supabase Storage (offline evaluation exports), in-memory buffer (telemetry retry queue) (013-platform-operations)

- Python 3.13 + LangGraph, LangChain Core, FastAPI, Pydantic v2, httpx (012-workflow-engine)
- No business data storage + Workflow checkpoints managed through LangGraph checkpoint interface (012-workflow-engine)

- Python 3.10+ (project requires >=3.13 per pyproject.toml) + FastAPI, uvicorn, supabase, openai, google-generativeai (001-project-foundation)

- Python 3.13+ + FastAPI, Pydantic v2 (already in project), python-multipart, httpx (014-api-layer)
- Stateless — no persistence, no database, no server-side session state (014-api-layer)

## Project Structure

```text
backend/
  src/
    agents/
    api/
      routes/
      v1/
      v2/
      dependencies.py
      middleware.py
      exception_handlers.py
      response.py
      api.py
    cache/
    config/
    models/
    modules/
      ai_generation/
      operations/
      workflow_engine/
    services/
  tests/
    unit/
      api/
    integration/
      api/
frontend/
specs/
```

## Commands

uv run ruff check .; uv run mypy backend/src backend/tests; uv run pytest

## Code Style

Python 3.10+ (project requires >=3.13 per pyproject.toml): Follow standard conventions

## Recent Changes
- 014-api-layer: Full implementation complete — 56 tasks, 42 tests, 31 files. Standardized JSON envelope, versioned routes, middleware stack, OpenAPI docs, global exception handlers, auth DI, all 11 v1 route wrappers. (2026-07-19)
- 013-platform-operations: Added Python 3.13+ + langsmith>=0.1.0, opentelemetry-api>=1.20.0, opentelemetry-sdk>=1.20.0, opentelemetry-exporter-otlp-proto-http>=1.20.0, pydantic>=2.0.0, supabase>=2.0.0


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
