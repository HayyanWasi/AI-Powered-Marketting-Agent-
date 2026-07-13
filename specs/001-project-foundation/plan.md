# Implementation Plan: Project Foundation - Project Setup & Configuration

**Branch**: `001-project-foundation` | **Date**: 2026-07-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-project-foundation/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Establish the core development infrastructure for the AI Social Campaign Manager:
UV package manager, Python dependencies (FastAPI, Supabase, OpenAI, etc.), code
quality tools (Black, Ruff, mypy), pytest with coverage, environment variable
management, project directory structure, Docker containerization, pre-commit hooks,
Python version enforcement, and gitignore configuration.

## Technical Context

**Language/Version**: Python 3.10+ (project requires >=3.13 per pyproject.toml)  
**Primary Dependencies**: FastAPI, uvicorn, supabase, openai, google-generativeai,
duckduckgo-search, Pillow, python-dotenv, pydantic, httpx  
**Storage**: N/A (foundation layer — no storage setup in this feature)  
**Testing**: pytest with pytest-cov and pytest-asyncio  
**Target Platform**: Linux server (Docker), cross-platform dev (Linux, macOS, Windows WSL2)  
**Project Type**: web (backend + frontend)  
**Performance Goals**: `uv sync` <2min, Docker build <5min, pre-commit hooks <30s  
**Constraints**: Python 3.10+, UV package manager, no hardcoded secrets, env-only config  
**Scale/Scope**: Single developer workstation setup — no production scale targets

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Test-First**: Tests written before implementation? (Principle I) — Foundation layer; pytest configured but no feature tests yet. Test framework is set up for future test-first work.
- [x] **Clean Code**: Type hints, dataclasses, docstrings, no print statements? (Principle II) — Black, Ruff, mypy configured to enforce this.
- [x] **KISS/DRY**: No over-engineering, no unnecessary abstractions? (Principle III) — Simple UV-based setup, no Redis, no RAG.
- [x] **Fail Gracefully**: Error handling for all external calls? (Principle IV) — Env var validation with clear error messages configured.
- [x] **Architecture**: Linear pipeline, no RAG, env-only config? (Principle V) — Env-only config enforced; no RAG; linear pipeline deferred to later features.
- [x] **Coverage**: >=80% code coverage target? (Principle VI) — pytest-cov configured; threshold enforcement deferred to later feature.
- [x] **Stack**: Uses approved tech stack (FastAPI, Supabase, Next.js, etc.)? — All dependencies match constitution.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-foundation/
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
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── campaigns.py
│   │   │   ├── company.py
│   │   │   ├── guest.py
│   │   │   └── webhook.py
│   │   └── dependencies.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── seminar.py
│   │   ├── contest.py
│   │   ├── community.py
│   │   ├── course.py
│   │   ├── entry_test.py
│   │   └── test_result.py
│   ├── orchestrator.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ddgs.py
│   │   ├── llm.py
│   │   ├── pollinations.py
│   │   ├── supabase.py
│   │   └── validation.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── guest.py
│   │   ├── campaign.py
│   │   ├── company.py
│   │   └── schemas.py
│   ├── cache/
│   │   ├── __init__.py
│   │   └── session.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── main.py
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .python-version
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── api/
│   │   ├── components/
│   │   ├── lib/
│   │   ├── types/
│   │   └── page.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

**Structure Decision**: Web application (Option 2) — backend (FastAPI/Python) +
frontend (Next.js/TypeScript). Directory structure matches constitution spec.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — all constitution checks pass. Complexity tracking not required.