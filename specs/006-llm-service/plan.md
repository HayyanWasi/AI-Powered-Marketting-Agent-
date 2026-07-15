# Implementation Plan: LLM Integration Service

**Branch**: `006-llm-service` | **Date**: 2026-07-15 | **Spec**: [specs/006-llm-service/spec.md](spec.md)
**Input**: Feature specification for unified OpenAI GPT-4o + Google Gemini LLM interface with system prompt management.

## Summary

Provide a unified interface for OpenAI GPT-4o (primary) and Google Gemini (fallback) with retry+fallback logic, streaming, named system prompt templates (variable injection via `{placeholder}`), and token usage tracking. Follows existing service pattern (sync, DI, custom exceptions) and model pattern (dataclass + Pydantic dual representation).

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: openai>=1.0.0, google-generativeai>=0.3.0, pydantic>=2.0.0 (all already installed)  
**Storage**: N/A — prompt templates defined in Python code, no database storage  
**Testing**: pytest>=7.4.0, pytest-cov>=4.1.0  
**Target Platform**: Linux server (FastAPI async, but services are sync)  
**Project Type**: single (backend service, same as existing)  
**Performance Goals**: <30s per LLM call (SC-001); fallback within 5s of retry exhaustion (SC-002)  
**Constraints**: Streaming has no fallback; lazy provider init (errors deferred to first request); no concurrent rate-limit coordination across requests  
**Scale/Scope**: Internal service used by campaign agents; single-instance, no user-facing rate limiting

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Test-First**: Tests written before implementation? (Principle I)
- [x] **Clean Code**: Type hints, dataclasses, docstrings, no print statements? (Principle II)
- [x] **KISS/DRY**: No over-engineering, no unnecessary abstractions? (Principle III)
- [x] **Fail Gracefully**: Error handling for all external calls? (Principle IV)
- [x] **Architecture**: Linear pipeline, no RAG, env-only config? (Principle V)
- [x] **Coverage**: >=80% code coverage target? (Principle VI)
- [x] **Stack**: Uses approved tech stack (FastAPI, Supabase, Next.js, etc.)?

All gates pass. No complexity justification needed.

## Project Structure

### Documentation (this feature)

```text
specs/006-llm-service/
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
│   ├── models/
│   │   └── llm.py                  # NEW: LLMResponse, LLMRequest models
│   ├── services/
│   │   └── llm_service.py          # NEW: LLMService (unified provider interface)
│   └── config/
│       └── prompts.py              # NEW: named system prompt templates
└── tests/
    ├── unit/
    │   ├── test_llm_service.py     # NEW (or extend existing test_llm_service.py)
    │   ├── test_llm_models.py      # NEW: model tests
    │   └── test_prompts.py         # NEW: prompt template tests
    └── integration/
        └── test_llm_api.py         # NEW: API endpoint tests
```

**Structure Decision**: Follows existing backend project structure. New module `services/llm_service.py` replaces the placeholder `services/llm.py` (which currently only wraps OpenAI for guest search). New `models/llm.py` and `config/prompts.py` are added. Existing `services/llm.py` will be renamed/refactored.

## Complexity Tracking

> No violations — all gates pass.
