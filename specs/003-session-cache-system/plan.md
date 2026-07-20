# Implementation Plan: Session Cache System

**Branch**: `003-session-cache-system` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-session-cache-system/spec.md`

## Summary

In-memory session cache for ephemeral guest data storage with 24-hour TTL. Implements FR-07: session ID generation, key-value data storage per session, TTL-based expiry, concurrent access handling, and manual cache cleanup. Uses Python dict with threading lock for thread safety per the project constitution's KISS principle (no Redis for V1).

## Technical Context

**Language/Version**: Python 3.10+ (project requires >=3.13)  
**Primary Dependencies**: Standard library only (uuid, threading, time, dataclasses) — no external packages  
**Storage**: In-memory (Python dict) — no database or persistence  
**Testing**: pytest with threading stress tests for concurrent access verification  
**Target Platform**: Linux server (Docker)  
**Project Type**: Backend library module  
**Performance Goals**: Session CRUD round-trip <50ms per SC-001; 100 concurrent ops across 50 sessions per SC-003  
**Constraints**: In-memory only; <1s for manual clear regardless of session count; 24-hour default TTL  
**Scale/Scope**: Ephemeral guest sessions only — no persistence across server restarts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Test-First**: Tests required before implementation — will generate tests in tasks.md (Principle I)
- [x] **Clean Code**: Type hints, dataclasses, docstrings, no print statements — all applicable (Principle II)
- [x] **KISS/DRY**: Dict-based cache explicitly endorsed; no Redis for V1 (Principle III)
- [x] **Fail Gracefully**: Error handling for expired/not-found sessions; no external calls to fail (Principle IV)
- [x] **Architecture**: Ephemeral guest data — never persisted to DB; env-only config for TTL; no RAG (Principle V)
- [x] **Coverage**: >=80% target achievable with unit + concurrency stress tests (Principle VI)
- [x] **Stack**: Uses Python 3.13 + FastAPI — approved stack; no new dependencies introduced

**Gate decision**: PASS — No violations. All non-negotiable principles are satisfied. Feature is simple enough that over-engineering is not a risk.

## Project Structure

### Documentation (this feature)

```text
specs/003-session-cache-system/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (interface contracts)
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
backend/src/
└── cache/               # New module under constitution's approved structure
    ├── __init__.py      # Public API exports
    ├── session.py       # Session data class
    └── cache.py         # SessionCache implementation (dict-based, thread-safe)
```

**Structure Decision**: Single module `backend/src/cache/` with three files. No frontend changes. No database migrations. Tests go under `backend/tests/unit/test_session_cache.py`.
