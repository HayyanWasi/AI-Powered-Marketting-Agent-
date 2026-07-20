# Tasks: Database & Storage Setup

**Input**: Design documents from `/specs/002-database-storage/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Install dependencies and configure environment for Supabase access

- [x] T001 Install python-multipart dependency in pyproject.toml
- [x] T002 Add SUPABASE_URL and SUPABASE_KEY to .env.example
- [x] T003 Add SUPABASE_URL and SUPABASE_KEY to settings.py in backend/src/config/settings.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create migration scripts directory at backend/migrations/
- [x] T005 Create CompanyProfile Pydantic model in backend/src/models/company.py
- [x] T006 Create SupabaseService skeleton in backend/src/services/supabase.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Marketing User Sets Up Company Brand Profile (Priority: P1) 🎯 MVP

**Goal**: Marketing user can create a company profile with name and tone, upload brand reference images, and verify the data is stored.

**Independent Test**: User can create a company profile via the API, upload up to 6 images, and retrieve the stored profile with image URLs.

### Implementation for User Story 1

- [x] T007 [P] [US1] Implement CompanyProfile dataclass in backend/src/models/company.py
- [x] T008 [P] [US1] Implement SupabaseService.create_profile in backend/src/services/supabase.py
- [x] T009 [P] [US1] Implement SupabaseService.get_profile in backend/src/services/supabase.py
- [x] T010 [P] [US1] Create POST /api/company endpoint in backend/src/api/routes/company.py
- [x] T011 [P] [US1] Create GET /api/company/{id} endpoint in backend/src/api/routes/company.py
- [x] T012 [P] [US1] Add name uniqueness validation (single-company mode) in backend/src/services/supabase.py
- [x] T013 [US1] Register company routes in backend/src/main.py
- [x] T014 [US1] Implement image validation (size <=10MB, format JPEG/PNG/WebP) in backend/src/services/supabase.py
- [x] T015 [US1] Implement SupabaseService.upload_image in backend/src/services/supabase.py
- [x] T016 [US1] Implement POST /api/company/{id}/brand-images endpoint in backend/src/api/routes/company.py

**Checkpoint**: User Story 1 complete - user can create profile, upload images, and retrieve data

---

## Phase 4: User Story 2 - Developer Manages Company Profiles via Service (Priority: P2)

**Goal**: Developer can update and delete company profiles programmatically through the service layer.

**Independent Test**: Developer can update a profile's name/tone, upload new images, and delete a profile via the API.

### Implementation for User Story 2

- [x] T017 [P] [US2] Implement SupabaseService.update_profile in backend/src/services/supabase.py
- [x] T018 [P] [US2] Implement SupabaseService.delete_profile in backend/src/services/supabase.py
- [x] T019 [P] [US2] Create PUT /api/company/{id} endpoint in backend/src/api/routes/company.py
- [x] T020 [P] [US2] Create DELETE /api/company/{id} endpoint in backend/src/api/routes/company.py
- [x] T021 [US2] Implement retry logic (3 attempts, exponential backoff) in backend/src/services/supabase.py
- [x] T022 [US2] Add user-friendly error messages for all failure modes in backend/src/services/supabase.py

**Checkpoint**: User Story 2 complete - full CRUD available via API

---

## Phase 5: User Story 3 - Developer Runs Database Migrations (Priority: P3)

**Goal**: Developer can create and roll back the company_profiles table schema using versioned SQL scripts.

**Independent Test**: Developer runs up migration, verifies table schema, runs down migration, verifies table removed.

### Implementation for User Story 3

- [x] T023 [P] [US3] Create up migration script in backend/migrations/001_create_company_profiles.up.sql
- [x] T024 [P] [US3] Create down migration script in backend/migrations/001_create_company_profiles.down.sql

**Checkpoint**: User Story 3 complete - schema is versioned and reversible

---

## Phase 6: Tests

**Purpose**: Achieve >=80% coverage across all service and endpoint code

- [x] T025 [P] Write unit tests for CompanyProfile model validation in backend/tests/unit/test_validation.py
- [x] T026 [P] Write unit tests for SupabaseService CRUD operations in backend/tests/unit/test_supabase_service.py
- [x] T027 [P] Write integration tests for company API endpoints in backend/tests/integration/test_company_api.py
- [x] T028 Run all tests and verify >=80% coverage

---

## Phase 7: Polish & Cleanup

- [x] T029 Update README.md with database setup instructions
- [x] T030 Run linter and type checker on all new files
- [x] T031 Update AGENTS.md with database-storage technologies

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Setup | T001-T003 | ✅ Complete |
| Phase 2: Foundational | T004-T006 | ✅ Complete |
| Phase 3: User Story 1 (P1) | T007-T016 | ✅ Complete |
| Phase 4: User Story 2 (P2) | T017-T022 | ✅ Complete |
| Phase 5: User Story 3 (P3) | T023-T024 | ✅ Complete |
| Phase 6: Tests | T025-T028 | ✅ Complete |
| Phase 7: Polish & Cleanup | T029-T031 | ✅ Complete |
| **Total** | **31** | **100%** |

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (create profile + upload images)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add Tests → Verify coverage → Finalize
