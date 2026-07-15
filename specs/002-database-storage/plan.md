# Implementation Plan: Database & Storage Setup

**Branch**: `002-database-storage` | **Date**: 2026-07-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-database-storage/spec.md`

## Summary

Set up Supabase PostgreSQL `company_profiles` table and Supabase Storage bucket for brand reference images. Implement a service abstraction class with full CRUD operations (create, read, update, delete), a multipart/form-data image upload endpoint, database migration scripts (up/down), image file validation (size <= 10MB), retry logic on network failures, and single-company mode (V1 constraint).

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: supabase (Python SDK), fastapi, python-multipart, Pillow (PIL), pydantic, httpx
**Storage**: Supabase PostgreSQL (company_profiles table) + Supabase Storage (public bucket for brand images)
**Testing**: pytest, pytest-cov, pytest-asyncio, unittest.mock (mock Supabase client)
**Target Platform**: Linux server (Docker), cross-platform dev (Windows, Linux, macOS)
**Project Type**: web (backend-only — no frontend changes in this feature)
**Performance Goals**: Single record CRUD <100ms, image upload <10s per image, >=80% test coverage
**Constraints**: Single-company V1 mode (only one profile at a time), 10MB max file size, env-only Supabase config, retry up to 3 attempts on network failures, no hardcoded secrets
**Scale/Scope**: Single company profile, up to 6 brand images, single developer workstation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Test-First**: Tests written before implementation? (Principle I) — Service abstraction enables mocking; tests will be written before production code per TDD.
- [x] **Clean Code**: Type hints, dataclasses, docstrings, no print statements? (Principle II) — Service will use type hints and Pydantic models; logger instead of print.
- [x] **KISS/DRY**: No over-engineering, no unnecessary abstractions? (Principle III) — Simple service wrapper, no repository pattern, no ORM abstraction beyond Supabase SDK.
- [x] **Fail Gracefully**: Error handling for all external calls? (Principle IV) — Retry logic on Supabase calls, user-friendly error messages, no raw exception exposure.
- [x] **Architecture**: Linear pipeline, no RAG, env-only config? (Principle V) — Env-only Supabase URL/key, no RAG/vector embeddings, simple key-value lookup by company_id.
- [x] **Coverage**: >=80% code coverage target? (Principle VI) — pytest-cov configured, service mockable for high coverage.
- [x] **Stack**: Uses approved tech stack (FastAPI, Supabase, Next.js, etc.)? — Supabase PostgreSQL + Storage, FastAPI, Pillow — all in constitution.

## Project Structure

### Documentation (this feature)

```text
specs/002-database-storage/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── services/
│   │   ├── __init__.py
│   │   └── supabase.py          # SupabaseService class
│   ├── models/
│   │   ├── __init__.py
│   │   └── company.py           # CompanyProfile dataclass + Pydantic schema
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── company.py       # Company CRUD + upload endpoints
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   └── main.py
├── migrations/
│   ├── 001_create_company_profiles.up.sql
│   └── 001_create_company_profiles.down.sql
└── tests/
    ├── __init__.py
    ├── unit/
    │   ├── __init__.py
    │   ├── test_supabase_service.py
    │   └── test_validation.py
    └── integration/
        ├── __init__.py
        └── test_company_api.py
```

**Structure Decision**: Backend-only feature extending the existing web application structure. New files go into `backend/src/services/supabase.py`, `backend/src/models/company.py`, `backend/src/api/routes/company.py`, and `backend/migrations/`. Test files go into `backend/tests/unit/` and `backend/tests/integration/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — all constitution checks pass. Complexity tracking not required.
