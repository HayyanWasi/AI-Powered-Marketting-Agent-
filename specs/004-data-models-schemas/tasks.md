# Tasks: Data Models & Schemas

**Input**: Design documents from `/specs/004-data-models-schemas/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/pydantic-schemas.md

**Status**: All 34 tasks completed ✅

## What was built

1. **Guest models** (`backend/src/models/guest.py`) — `Guest` dataclass +
 `GuestCreate`/`GuestUpdate`/`GuestResponse` Pydantic schemas. Name required (1–255 chars, non-blank), title/company/bio optional (max 1000 chars). `to_response()` method for dataclass→Pydantic conversion
2. **Campaign models** (`backend/src/models/campaign.py`) — `Campaign` dataclass + `CampaignCreate`/`CampaignUpdate`/`CampaignResponse` Pydantic schemas. Type/caption required, image_url optional (validated URL), status defaults to "draft" with enum validation
3. **Company profile models** (`backend/src/models/company.py`) — Verified existing `CompanyProfile` dataclass + Pydantic schemas. Added `to_response()`, reference_image_urls list (max 6), name (1–255), tone (1–1000) validation
4. **Module exports** (`backend/src/models/__init__.py`) — Re-exports all models for clean `from src.models import Guest, Campaign, CompanyProfile` imports
5. **Tests** — 21 tests across 3 user stories: Guest (7 tests), Campaign (7 tests), Company Profile (7 tests) — validation, serialization round-trip, edge cases

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Update module exports

- [X] T001 Update `backend/src/models/__init__.py` to export `Guest`, `GuestCreate`, `GuestUpdate`, `GuestResponse`, `Campaign`, `CampaignCreate`, `CampaignUpdate`, `CampaignResponse`

---

## Phase 2: User Story 1 - Guest Profile Structure (Priority: P1) 🎯 MVP

**Goal**: Guest model with dataclass + Pydantic schemas supporting create, update, and response operations with validation.

**Independent Test**: Create a Guest dataclass with all fields, serialize to JSON via Pydantic GuestResponse, deserialize back, verify no data loss. Attempt creating GuestCreate with empty name — verify it raises validation error.

### Tests for User Story 1

- [X] T002 [P] [US1] Unit test for Guest dataclass default field values and instantiation in `backend/tests/unit/test_guest_model.py`
- [X] T003 [P] [US1] Unit test for GuestCreate validates required name field — empty/whitespace rejected in `backend/tests/unit/test_guest_model.py`
- [X] T004 [P] [US1] Unit test for GuestCreate accepts optional fields (title, company, bio) when omitted in `backend/tests/unit/test_guest_model.py`
- [X] T005 [P] [US1] Unit test for GuestUpdate all fields optional — partial updates accepted in `backend/tests/unit/test_guest_model.py`
- [X] T006 [P] [US1] Unit test for GuestResponse serializes to JSON and deserializes back with zero data loss in `backend/tests/unit/test_guest_model.py`
- [X] T007 [US1] Unit test for Guest dataclass to_response() conversion matches GuestResponse in `backend/tests/unit/test_guest_model.py`

### Implementation for User Story 1

- [X] T008 [US1] Create `Guest` dataclass in `backend/src/models/guest.py` with fields: name, title, company, bio and to_response() method
- [X] T009 [US1] Create `GuestCreate` Pydantic schema in `backend/src/models/guest.py` with name (required, 1-255 chars), title/company/bio (optional, max 1000 chars)
- [X] T010 [US1] Create `GuestUpdate` Pydantic schema in `backend/src/models/guest.py` with all fields optional
- [X] T011 [US1] Create `GuestResponse` Pydantic schema in `backend/src/models/guest.py` with id, name, title, company, bio, created_at, updated_at

**Checkpoint**: US1 complete — Guest model fully defined with dataclass + Pydantic schemas, all validation passing.

---

## Phase 3: User Story 2 - Campaign Data Structure (Priority: P1)

**Goal**: Campaign model with dataclass + Pydantic schemas supporting create, update, and response operations with status/type validation.

**Independent Test**: Create a Campaign dataclass with valid type and caption, serialize/deserialize via Pydantic. Attempt creating CampaignCreate with empty caption — verify rejection. Attempt invalid status value — verify rejection.

### Tests for User Story 2

- [X] T012 [P] [US2] Unit test for Campaign dataclass default field values and instantiation in `backend/tests/unit/test_campaign_model.py`
- [X] T013 [P] [US2] Unit test for CampaignCreate validates required type and caption fields in `backend/tests/unit/test_campaign_model.py`
- [X] T014 [P] [US2] Unit test for CampaignCreate rejects empty caption in `backend/tests/unit/test_campaign_model.py`
- [X] T015 [P] [US2] Unit test for CampaignCreate status defaults to "draft" and accepts valid status values in `backend/tests/unit/test_campaign_model.py`
- [X] T016 [P] [US2] Unit test for CampaignCreate image_url accepts valid URL and rejects invalid URL in `backend/tests/unit/test_campaign_model.py`
- [X] T017 [P] [US2] Unit test for CampaignResponse serializes to JSON and deserializes back with zero data loss in `backend/tests/unit/test_campaign_model.py`
- [X] T018 [US2] Unit test for Campaign dataclass to_response() conversion matches CampaignResponse in `backend/tests/unit/test_campaign_model.py`

### Implementation for User Story 2

- [X] T019 [US2] Create `Campaign` dataclass in `backend/src/models/campaign.py` with fields: type, caption, image_url, status and to_response() method
- [X] T020 [US2] Create `CampaignCreate` Pydantic schema in `backend/src/models/campaign.py` with type/caption required, image_url (optional HttpUrl), status (optional, default "draft")
- [X] T021 [US2] Create `CampaignUpdate` Pydantic schema in `backend/src/models/campaign.py` with all fields optional
- [X] T022 [US2] Create `CampaignResponse` Pydantic schema in `backend/src/models/campaign.py` with id, type, caption, image_url, status, created_at, updated_at

**Checkpoint**: US2 complete — Campaign model fully defined with dataclass + Pydantic schemas, all validation passing.

---

## Phase 4: User Story 3 - Company Profile Structure (Priority: P1)

**Goal**: Company model already exists — verify it meets spec requirements and add standalone tests.

**Independent Test**: Create a CompanyProfile dataclass with name and tone, convert via to_response(), serialize to JSON, deserialize back. Attempt empty name — verify rejection.

### Tests for User Story 3

- [X] T023 [P] [US3] Unit test for CompanyProfile dataclass default values and instantiation in `backend/tests/unit/test_company_model.py`
- [X] T024 [P] [US3] Unit test for CompanyProfileCreate validates required name and tone in `backend/tests/unit/test_company_model.py`
- [X] T025 [P] [US3] Unit test for CompanyProfileCreate rejects empty name in `backend/tests/unit/test_company_model.py`
- [X] T026 [P] [US3] Unit test for CompanyProfileUpdate all fields optional — partial updates accepted in `backend/tests/unit/test_company_model.py`
- [X] T027 [P] [US3] Unit test for CompanyProfileResponse serializes to JSON and deserializes with zero data loss in `backend/tests/unit/test_company_model.py`
- [X] T028 [P] [US3] Unit test for CompanyProfile to_response() and reference_image_urls handling in `backend/tests/unit/test_company_model.py`
- [X] T029 [US3] Unit test for CompanyProfile reference_image_urls max 6 items enforced in `backend/tests/unit/test_company_model.py`

### Implementation for User Story 3

- [X] T030 [US3] Verify and update `backend/src/models/company.py` — ensure CompanyProfile dataclass has to_response() and all Pydantic schemas match spec (name 1-255 chars, tone 1-1000 chars)

**Checkpoint**: US3 complete — Company model verified with standalone tests, all validation passing.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Lint, type-check, and verify end-to-end correctness.

- [X] T031 Run `ruff check .` on `backend/src/models/` and `backend/tests/unit/test_*_model.py`, fix any issues
- [X] T032 Run `mypy` on `backend/src/models/` and fix any type errors
- [X] T033 Run `pytest` on `backend/tests/unit/test_*_model.py` and verify all tests pass
- [X] T034 Verify coverage meets 100% target on model modules

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **US1 (Phase 2)**: Depends on Setup — adds Guest model files
- **US2 (Phase 3)**: Depends on Setup — adds Campaign model files (parallelizable with US1)
- **US3 (Phase 4)**: Depends on Setup — verifies existing Company model
- **Polish (Phase 5)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: No story dependencies — standalone
- **US2 (P1)**: No story dependencies — standalone
- **US3 (P1)**: No story dependencies — standalone (existing code)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Dataclass before Pydantic schemas
- Basic fields before validation rules
- Story complete before moving to next phase

### Parallel Opportunities

- All Phase 1-3 stories can run in parallel (different files: guest.py, campaign.py, company.py)
- All test tasks within a phase marked [P] can run in parallel
- Each story's implementation depends on its own tests passing first

---

## Parallel Example: All Three Stories Simultaneously

```bash
# Launch all tests together (all should fail — not implemented yet):
pytest backend/tests/unit/test_guest_model.py backend/tests/unit/test_campaign_model.py backend/tests/unit/test_company_model.py

# Implement all three models in parallel:
# Task: Create guest.py with dataclass + schemas
# Task: Create campaign.py with dataclass + schemas
# Task: Verify company.py patterns

# Verify all:
pytest backend/tests/unit/test_guest_model.py backend/tests/unit/test_campaign_model.py backend/tests/unit/test_company_model.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: US1 (Guest model)
3. **STOP and VALIDATE**: Test Guest independently — valid/invalid data, serialization round-trip
4. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup → Foundation ready
2. Add US1 (Guest) → Test independently
3. Add US2 (Campaign) → Test independently
4. Add US3 (Company verification) → Test independently
5. Polish → All tests pass together

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup together
2. Once Setup is done (parallel):
   - Developer A: US1 — Guest model
   - Developer B: US2 — Campaign model
   - Developer C: US3 — Company verification + tests
3. All stories are independent — no merge conflicts expected
4. Final Polish done together

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Tests MUST be written and confirmed failing before implementation (Constitution Principle I)
- Company model already exists — US3 focuses on test coverage and pattern alignment
- All three stories are P1 priority and can be implemented in parallel
- Total: 34 tasks (1 Setup + 6 US1 tests + 4 US1 impl + 7 US2 tests + 4 US2 impl + 7 US3 tests + 1 US3 impl + 4 Polish)

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Setup | T001 | ✅ Complete |
| Phase 2: US1 — Guest Model | T002-T011 | ✅ Complete |
| Phase 3: US2 — Campaign Model | T012-T022 | ✅ Complete |
| Phase 4: US3 — Company Profile | T023-T030 | ✅ Complete |
| Phase 5: Polish & Cross-Cutting | T031-T034 | ✅ Complete |
| **Total** | **34** | **100%** |
