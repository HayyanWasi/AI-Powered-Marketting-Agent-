# Tasks: Session Cache System

**Input**: Design documents from `/specs/003-session-cache-system/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/session-cache-interface.md

**Status**: All 32 tasks completed ✅

## What was built

1. **Session dataclass** (`backend/src/cache/session.py`) — `Session` with `session_id`, `data` dict, `created_at`, `last_activity` fields
2. **SessionCache class** (`backend/src/cache/cache.py`) — In-memory thread-safe dict cache with `RLock`. Methods: `create_session`, `get_session`, `session_exists`, `store_data`, `get_data`, `update_data`, `delete_data`, `delete_session`, `clear_all`, `clear_expired`
3. **TTL expiry** — Configurable TTL (default 24h), lazy expiry check on every access, `last_activity` refresh on read/write (except `session_exists`), `ValueError` for TTL ≤ 0
4. **Clear operations** — `clear_all()` removes all sessions (no-op on empty), `clear_expired()` removes only expired sessions and returns count
5. **Thread safety** — All methods use `threading.RLock` for corruption-free concurrent access
6. **Tests** — 27 tests across 3 user stories: session CRUD, data isolation, TTL expiry, activity refresh, clear operations, concurrent stress test (100 ops across 50 sessions)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module directory structure creation

- [x] T001 Create `backend/src/cache/` module directory with `__init__.py` that exports `SessionCache` from `backend/src/cache/cache.py`

---

## Phase 2: User Story 1 - Guest User Maintains Ephemeral State (Priority: P1) 🎯 MVP

**Goal**: Guest users can create a session, store, retrieve, update, and delete key-value data. Multiple sessions are isolated.

**Independent Test**: Create a guest session, store three different data entries, retrieve each by key, update one, delete another, and verify the remaining data is correct. A different session ID cannot access the data.

### Tests for User Story 1

- [x] T002 [P] [US1] Unit test for Session dataclass fields and defaults in `backend/tests/unit/test_session_cache.py`
- [x] T003 [P] [US1] Unit test for create_session returns unique UUID4 and stores session in `backend/tests/unit/test_session_cache.py`
- [x] T004 [P] [US1] Unit test for store_data, get_data, update_data, delete_data round-trip in `backend/tests/unit/test_session_cache.py`
- [x] T005 [P] [US1] Unit test for session_exists and get_session with valid/non-existent IDs in `backend/tests/unit/test_session_cache.py`
- [x] T006 [P] [US1] Unit test for session isolation — data stored in one session is not accessible from another in `backend/tests/unit/test_session_cache.py`
- [x] T007 [US1] Unit test for delete_session removes session and all its data in `backend/tests/unit/test_session_cache.py`

### Implementation for User Story 1

- [x] T008 [P] [US1] Create `Session` dataclass in `backend/src/cache/session.py` with fields: session_id (str), data (dict), created_at (float), last_activity (float)
- [x] T009 [US1] Implement `SessionCache` class in `backend/src/cache/cache.py` with constructor (ttl param, RLock, sessions dict) and methods: create_session, get_session, session_exists, store_data, get_data, update_data, delete_data, delete_session

**Checkpoint**: US1 complete — sessions can be created, data stored/retrieved/updated/deleted, sessions isolated from each other.

---

## Phase 3: User Story 2 - System Prevents Use of Stale Session Data (Priority: P2)

**Goal**: Sessions automatically expire after TTL seconds of inactivity. Stale data is never served. Activity refreshes the expiry timer.

**Independent Test**: Create a cache with 1ms TTL, create a session, store data, wait 2ms, verify session_exists returns False and get_data returns (None, False). Create another session, perform a read operation within TTL, verify the expiry timer resets.

### Tests for User Story 2

- [x] T010 [P] [US2] Unit test for session expiry after TTL in `backend/tests/unit/test_session_cache.py`
- [x] T011 [P] [US2] Unit test that expired session returns (None, False) from get_data in `backend/tests/unit/test_session_cache.py`
- [x] T012 [P] [US2] Unit test that read operations refresh last_activity timestamp in `backend/tests/unit/test_session_cache.py`
- [x] T013 [P] [US2] Unit test that write operations refresh last_activity timestamp in `backend/tests/unit/test_session_cache.py`
- [x] T014 [P] [US2] Unit test that session_exists does NOT refresh last_activity timestamp in `backend/tests/unit/test_session_cache.py`
- [x] T015 [US2] Unit test for zero/negative TTL raises ValueError in `backend/tests/unit/test_session_cache.py`

### Implementation for User Story 2

- [x] T016 [US2] Add lazy expiry check to get_session, store_data, get_data, update_data, delete_data, delete_session, session_exists in `backend/src/cache/cache.py`
- [x] T017 [US2] Add last_activity refresh on every read/write operation in `backend/src/cache/cache.py` (get_data, store_data, update_data, delete_data, delete_session, get_session)
- [x] T018 [US2] Ensure session_exists does NOT refresh last_activity in `backend/src/cache/cache.py`
- [x] T019 [US2] Add ValueError for ttl <= 0 in SessionCache constructor in `backend/src/cache/cache.py`

**Checkpoint**: US2 complete — expired sessions return "not found", activity resets TTL, stale data never served.

---

## Phase 4: User Story 3 - Administrator Manually Clears Session Cache (Priority: P3)

**Goal**: Administrators can clear all sessions or only expired sessions on demand. Cache handles concurrent operations safely.

**Independent Test**: Create multiple sessions, let some expire, invoke clear_expired, verify only expired sessions removed. Then invoke clear_all, verify zero sessions remain. Run 100 concurrent ops across 50 sessions without corruption.

### Tests for User Story 3

- [x] T020 [P] [US3] Unit test for clear_all removes all sessions in `backend/tests/unit/test_session_cache.py`
- [x] T021 [P] [US3] Unit test for clear_all on empty cache succeeds without error in `backend/tests/unit/test_session_cache.py`
- [x] T022 [P] [US3] Unit test for clear_expired removes only expired sessions in `backend/tests/unit/test_session_cache.py`
- [x] T023 [P] [US3] Unit test for clear_expired preserves active sessions in `backend/tests/unit/test_session_cache.py`
- [x] T024 [P] [US3] Unit test for clear_expired returns count of removed sessions in `backend/tests/unit/test_session_cache.py`
- [x] T025 [US3] Concurrency stress test — 100 concurrent ops across 50 sessions without corruption in `backend/tests/unit/test_session_cache.py`

### Implementation for User Story 3

- [x] T026 [US3] Implement clear_all in `backend/src/cache/cache.py` — removes all sessions, no-op on empty cache
- [x] T027 [US3] Implement clear_expired in `backend/src/cache/cache.py` — removes only expired sessions, returns count
- [x] T028 [US3] Ensure all SessionCache methods use RLock for thread safety in `backend/src/cache/cache.py`

**Checkpoint**: US3 complete — manual clear operations work correctly, concurrent access is safe.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Lint, type-check, and verify end-to-end correctness.

- [x] T029 Run `ruff check .` on `backend/src/cache/` and `backend/tests/unit/test_session_cache.py`, fix any issues
- [x] T030 Run `mypy` on `backend/src/cache/` and fix any type errors
- [x] T031 Run `pytest` on `backend/tests/unit/test_session_cache.py` and verify all 20+ tests pass
- [x] T032 Verify coverage meets >=80% target on cache module

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **US1 (Phase 2)**: Depends on Setup completion
- **US2 (Phase 3)**: Depends on US1 implementation (T008, T009) — adds expiry to existing operations
- **US3 (Phase 4)**: Depends on US2 implementation (T016-T019) — adds clear operations to thread-safe cache
- **Polish (Phase 5)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: No story dependencies — standalone MVP
- **US2 (P2)**: Depends on US1 — adds TTL expiry to existing SessionCache methods
- **US3 (P3)**: Depends on US1 + US2 — adds clear operations to existing SessionCache

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services (Session dataclass before SessionCache)
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Phase 2 test tasks (T002-T007) can run in parallel — they test different methods
- All Phase 3 test tasks (T010-T015) can run in parallel
- All Phase 4 test tasks (T020-T025) can run in parallel except T025 depends on concurrent implementation
- Within a user story, tests and implementation are sequential (test-first)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (written first, should fail):
pytest backend/tests/unit/test_session_cache.py -k "test_session_dataclass or test_create_session or test_data_crud or test_session_exists or test_session_isolation or test_delete_session"
# Expected: all fail (not implemented yet)

# Launch all models for User Story 1 together:
# Task: Create Session dataclass in backend/src/cache/session.py
# Task: Create SessionCache in backend/src/cache/cache.py

# Verify US1:
pytest backend/tests/unit/test_session_cache.py -k "test_session_dataclass or test_create_session or test_data_crud or test_session_exists or test_session_isolation or test_delete_session"
# Expected: all pass
```

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together (written first, should fail):
pytest backend/tests/unit/test_session_cache.py -k "test_expiry or test_expired_data or test_read_refreshes or test_write_refreshes or test_exists_no_refresh or test_zero_ttl"

# Implementation then added to SessionCache

# Verify US2:
pytest backend/tests/unit/test_session_cache.py -k "test_expiry or test_expired_data or test_read_refreshes or test_write_refreshes or test_exists_no_refresh or test_zero_ttl"
```

## Parallel Example: User Story 3

```bash
# Launch all tests (should fail initially):
pytest backend/tests/unit/test_session_cache.py -k "test_clear_all or test_clear_all_empty or test_clear_expired_only or test_clear_expired_preserves or test_clear_expired_count or test_concurrent"

# After implementation:
pytest backend/tests/unit/test_session_cache.py -k "test_clear_all or test_clear_all_empty or test_clear_expired_only or test_clear_expired_preserves or test_clear_expired_count or test_concurrent"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: US1 (session CRUD + data CRUD)
3. **STOP and VALIDATE**: Test US1 independently — sessions created, data stored/retrieved/updated/deleted, sessions isolated
4. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup → Foundation ready
2. Add US1 (session + data CRUD) → Test independently → Deploy/Demo (MVP!)
3. Add US2 (TTL expiry) → Test independently → Deploy/Demo
4. Add US3 (clear + concurrency) → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup together
2. Once Setup is done:
   - Developer A: US1 (session + data CRUD)
   - Developer B: Waits for US1, then US2 (TTL)
   - Developer C: Waits for US2, then US3 (clear + concurrency)
3. Stories build incrementally but verify independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests MUST be written and confirmed failing before implementation (Test-First per Constitution Principle I)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total: 32 tasks (7 Setup/US1 tests + 2 US1 impl + 6 US2 tests + 4 US2 impl + 6 US3 tests + 3 US3 impl + 3 tests + 1 Polish test verification + 3 lint/type/coverage)

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Setup | T001 | ✅ Complete |
| Phase 2: US1 — Session CRUD | T002-T009 | ✅ Complete |
| Phase 3: US2 — TTL Expiry | T010-T019 | ✅ Complete |
| Phase 4: US3 — Clear & Concurrency | T020-T028 | ✅ Complete |
| Phase 5: Polish & Cross-Cutting | T029-T032 | ✅ Complete |
| **Total** | **32** | **100%** |
