# Implementation Plan: Data Models & Schemas

**Branch**: `004-data-models-schemas` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-data-models-schemas/spec.md`

## Summary

Define all core data structures as Python dataclasses (internal representation) and Pydantic schemas (API validation layer) for Guest, Campaign, and Company entities. Company models already exist (`backend/src/models/company.py`); this feature adds Guest and Campaign models and ensures all three follow consistent patterns: dataclass for internal use, Pydantic BaseModel for API request/response validation, type hints, field constraints, and serialization support.

## Technical Context

**Language/Version**: Python 3.10+ (project requires >=3.13)  
**Primary Dependencies**: pydantic (already in project), dataclasses (stdlib)  
**Storage**: N/A — models define data shape, not storage  
**Testing**: pytest with 100% coverage target on all model modules  
**Target Platform**: Linux server (Docker)  
**Project Type**: Backend library module (models layer)  
**Performance Goals**: Model instantiation <10ms; serialization/deserialization <5ms  
**Constraints**: No external service calls; models are pure data transformations; must match Supabase column types for Company  
**Scale/Scope**: 3 data models (Guest, Campaign, Company) with Pydantic request/response schemas for each

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Test-First**: Tests required before implementation — will be generated in tasks.md (Principle I)
- [x] **Clean Code**: Type hints, dataclasses, Pydantic schemas, no print statements (Principle II)
- [x] **KISS/DRY**: Reuse existing Company model pattern for Guest and Campaign; no over-engineering (Principle III)
- [x] **Fail Gracefully**: Pydantic validation produces clear field-level errors automatically (Principle IV)
- [x] **Architecture**: Pure data layer — no external calls, no orchestration (Principle V)
- [x] **Coverage**: Target 100% on model modules — easily achievable for pure data structures (Principle VI)
- [x] **Stack**: Uses approved Python 3.13 + FastAPI + Pydantic stack; no new dependencies introduced

**Gate decision**: PASS — No violations. All principles satisfied with existing stack.

## Project Structure

### Documentation (this feature)

```text
specs/004-data-models-schemas/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (Pydantic schema contracts)
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
backend/src/
└── models/              # Existing directory, will add new files
    ├── __init__.py      # Public exports for all models
    ├── company.py       # Existing — keep as-is, verify patterns
    ├── guest.py         # NEW - Guest dataclass + Pydantic schemas
    └── campaign.py      # NEW - Campaign dataclass + Pydantic schemas
```

**Structure Decision**: Add `guest.py` and `campaign.py` to existing `backend/src/models/` directory. Follow the same pattern as `company.py` (dataclass for internal + Pydantic BaseModel for API). No frontend changes. No database migrations.
