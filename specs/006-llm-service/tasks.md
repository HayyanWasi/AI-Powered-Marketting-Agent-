# Tasks: LLM Integration Service

**Input**: Design documents from `specs/006-llm-service/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Per spec.md, each user story includes "Independent Test" verification criteria. No automated test tasks are generated — tests are only added if explicitly requested.

**Status**: All 25 tasks completed ✅

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## What was built

1. **Data Models** (`backend/src/models/llm.py`) — `TokenUsage` (dataclass + Pydantic `TokenUsageData`), `LLMResponse` (dataclass + Pydantic `LLMResponseData`), `StreamChunk` (dataclass), `LLMRequest` (Pydantic input schema)

2. **LLM Service** (`backend/src/services/llm_service.py`) — `LLMService` unified interface with `OpenAIProvider` (GPT-4o primary) and `GeminiProvider` (Gemini fallback), retry with exponential backoff (3 attempts, 1s/2s/4s), automatic fallback on transient errors, streaming via `generate_stream()`, named template resolution, token usage tracking, lazy provider initialization

3. **Prompt Templates** (`backend/src/config/prompts.py`) — `PROMPT_TEMPLATES` dict, `render_template()` with `{variable}` injection (missing vars left as-is), `register_template()` for campaign agents

4. **Tests** — 30 new tests across 3 files:
   - `test_llm_models.py` (8 tests): model defaults, to_response(), Pydantic validation
   - `test_prompts.py` (8 tests): render_template, register_template, missing vars, duplicates
   - `test_llm_service_new.py` (14 tests): OpenAI/Gemini providers, generate/stream, retry/fallback, templates, error cases

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Web app: `backend/src/`, `backend/tests/`
- All paths relative to repository root

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create new source files for the LLM service feature.

- [X] T001 [P] Create model module at `backend/src/models/llm.py` with dataclass and pydantic imports
- [X] T002 [P] Create service module at `backend/src/services/llm_service.py` with provider imports
- [X] T003 [P] Create prompt templates config at `backend/src/config/prompts.py` with PROMPT_TEMPLATES dict

---

## Phase 2: Foundational (Data Models)

**Purpose**: Core data models that ALL user stories depend on. Must complete before any story begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Implement TokenUsage dataclass and TokenUsageData Pydantic model in `backend/src/models/llm.py`
- [X] T005 Implement StreamChunk dataclass in `backend/src/models/llm.py`
- [X] T006 Implement LLMResponse dataclass, LLMResponseData Pydantic model, and LLMRequest Pydantic model in `backend/src/models/llm.py`
- [X] T007 Export all new models from `backend/src/models/__init__.py`

**Checkpoint**: Foundation ready — models can be imported and used by any story.

---

## Phase 3: User Story 1 - Generate Text via Default LLM Provider (Priority: P1) 🎯 MVP

**Goal**: Unified interface that sends a prompt to OpenAI GPT-4o, retries on transient failures (3 attempts, exponential backoff), falls back to Gemini on retry exhaustion, and returns a normalized response. Supports inline system prompts only (template integration in US3).

**Independent Test**: Call `LLMService.generate()` with a simple prompt and verify a text response is returned with provider and model metadata.

- [X] T008 [US1] Implement OpenAIProvider internal class with generate() method in `backend/src/services/llm_service.py`
- [X] T009 [US1] Implement GeminiProvider internal class with generate() method in `backend/src/services/llm_service.py`
- [X] T010 [US1] Implement retry logic (3 attempts, 1s/2s/4s exponential backoff) for transient failures in `backend/src/services/llm_service.py`
- [X] T011 [US1] Implement LLMService exception classes (LLMServiceError, LLMProviderError, LLMTemplateNotFoundError) in `backend/src/services/llm_service.py`
- [X] T012 [US1] Implement LLMService.generate() with primary+fallback orchestration in `backend/src/services/llm_service.py`
- [X] T013 [US1] Add LLMService to module exports in `backend/src/services/__init__.py`

**Checkpoint**: US1 fully functional — text generation with retry and fallback works independently.

---

## Phase 4: User Story 2 - Stream Text from LLM (Priority: P2)

**Goal**: Token-by-token streaming from the unified interface. No fallback on streaming errors — propagates immediately. Normalizes streaming contract across OpenAI and Gemini.

**Independent Test**: Call `LLMService.generate_stream()` with a prompt and verify multiple partial StreamChunk objects are received before a final chunk with `finished=True`.

- [X] T014 [US2] Implement OpenAIProvider.generate_stream() yielding StreamChunk in `backend/src/services/llm_service.py`
- [X] T015 [US2] Implement GeminiProvider.generate_stream() yielding StreamChunk in `backend/src/services/llm_service.py`
- [X] T016 [US2] Implement LLMService.generate_stream() with streaming orchestration in `backend/src/services/llm_service.py`

**Checkpoint**: US2 fully functional — streaming works independently of templates and token tracking.

---

## Phase 5: User Story 3 - Use Named System Prompt Templates (Priority: P2)

**Goal**: Named prompt templates with `{variable}` injection stored in Python code. Integrates with LLMService when `template_name` is provided in LLMRequest.

**Independent Test**: Define a template with placeholders, call `LLMService.generate()` with `template_name` and variables, verify the rendered system prompt is sent to the LLM.

- [X] T017 [P] [US3] Implement PROMPT_TEMPLATES dict, render_template(), and register_template() in `backend/src/config/prompts.py`
- [X] T018 [US3] Integrate template resolution into LLMService.generate() in `backend/src/services/llm_service.py`
- [X] T019 [US3] Integrate template resolution into LLMService.generate_stream() in `backend/src/services/llm_service.py`

**Checkpoint**: US3 fully functional — named templates work with both generate and generate_stream.

---

## Phase 6: User Story 4 - Track Token Usage (Priority: P3)

**Goal**: Token counts (prompt, completion, total) returned with every response, labeled by provider. Streaming accumulates counts into final aggregated response.

**Independent Test**: Send a known prompt and verify the response includes prompt_tokens, completion_tokens, and total_tokens from the provider.

- [X] T020 [US4] Ensure token counts are populated from provider-native metadata in LLMService.generate() in `backend/src/services/llm_service.py`
- [X] T021 [US4] Accumulate token counts across streaming chunks and populate in final aggregated response in `backend/src/services/llm_service.py`

**Checkpoint**: US4 fully functional — all response paths include labeled token counts.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, logging, and verification across all user stories.

- [X] T022 [P] Add structured logging for all LLM service operations (provider selection, retries, fallbacks, errors) in `backend/src/services/llm_service.py`
- [X] T023 [P] Add logging for template rendering operations in `backend/src/config/prompts.py`
- [X] T024 Verify ruff linting passes: `uv run ruff check backend/src/models/llm.py backend/src/services/llm_service.py backend/src/config/prompts.py`
- [X] T025 Verify mypy type checking passes: `uv run mypy backend/src/models/llm.py backend/src/services/llm_service.py backend/src/config/prompts.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — foundational models required
- **US2 (Phase 4)**: Depends on Phase 3 — needs provider classes from US1
- **US3 (Phase 5)**: Depends on Phase 3 — needs generate() to integrate templates with
- **US4 (Phase 6)**: Depends on Phases 3 + 4 — needs both generate() and generate_stream() to add token tracking
- **Polish (Phase 7)**: Depends on all prior phases

### User Story Dependencies

| Story | Priority | Depends On | Can Start After |
|-------|----------|------------|-----------------|
| US1 | P1 | Phase 2 (models) | Phase 2 complete |
| US2 | P2 | US1 (provider classes) | Phase 3 (US1) complete |
| US3 | P2 | US1 (generate method) | Phase 3 (US1) complete |
| US4 | P3 | US1 + US2 (both paths) | Phases 3 + 4 complete |

### Within Each User Story

- Models before services
- Core implementation before integration
- Provider implementations before service orchestration
- Each story is independently testable after its phase completes

### Parallel Opportunities

- **Phase 1**: T001, T002, T003 are all [P] — different files, no dependencies
- **Phase 5**: T017 is [P] — different file from T018/T019
- **Phase 7**: T022 is [P] — different file from T023; T024/T025 are linting
- **Phase 3 vs Phase 4**: US2 depends on US1 (same file) — must be sequential
- **Phase 3 vs Phase 5**: US3 depends on US1 — must be sequential

---

## Parallel Example: User Story 3

```bash
# T017 is in a different file — can run in parallel:
# File 1: backend/src/config/prompts.py
# File 2: backend/src/services/llm_service.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (models)
3. Complete Phase 3: User Story 1 (generate with retry+fallback)
4. **STOP and VALIDATE**: Test US1 independently via `LLMService.generate()`
5. Deploy/demo if ready

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready
2. Add US1 → Test independently → Deploy/Demo (MVP!)
3. Add US2 → Test independently → Deploy/Demo
4. Add US3 → Test independently → Deploy/Demo
5. Add US4 → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Sequential Implementation (Recommended)

Single developer should follow phase order. US2 and US3 are P2 and can be swapped after US1 complete.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Setup | T001-T003 | ✅ Complete |
| Phase 2: Foundational (Models) | T004-T007 | ✅ Complete |
| Phase 3: US1 — Generate Text via Default LLM Provider (P1) | T008-T013 | ✅ Complete |
| Phase 4: US2 — Stream Text from LLM (P2) | T014-T016 | ✅ Complete |
| Phase 5: US3 — Named System Prompt Templates (P2) | T017-T019 | ✅ Complete |
| Phase 6: US4 — Track Token Usage (P3) | T020-T021 | ✅ Complete |
| Phase 7: Polish & Cross-Cutting | T022-T025 | ✅ Complete |
| **Total** | **25** | **100%** |
