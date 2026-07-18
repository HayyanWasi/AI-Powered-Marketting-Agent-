---

description: "Task list for Company Profile Service feature implementation"
---

# Tasks: Company Profile Service

**Input**: Design documents from `/specs/009-company-profile-service/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Prepare the project structure required for Company Profile management.

- [ ] T001 Create Company Profile module structure in `src/modules/company/`
- [ ] T002 Create Company Profile configuration files in `src/config/company/`
- [ ] T003 Create Company Profile constants in `src/constants/company.py`

---

## Phase 2: Foundational Components

**Purpose**: Build the shared components required by all user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Create Company Profile entity in `src/models/company_profile.py`
- [ ] T005 [P] Create Brand Reference Image entity in `src/models/brand_reference_image.py`
- [ ] T006 [P] Implement Company validation rules in `src/validators/company_validator.py`
- [ ] T007 Implement Company repository in `src/repositories/company_repository.py`
- [ ] T008 Implement Brand Image repository in `src/repositories/brand_image_repository.py`

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Create a New Company Profile (Priority: P1) 🎯 MVP

**Goal**: Allow marketing organizers to create a new company profile containing company information and brand guidelines.

**Independent Test**: Create a company profile using a unique company name and verify that it is stored and retrievable.

### Implementation

- [ ] T009 [US1] Implement Create Company Profile service in `src/services/company/create_company_service.py`
- [ ] T010 [US1] Validate unique company names in `src/services/company/company_validation_service.py`
- [ ] T011 [US1] Validate required company information in `src/services/company/company_validation_service.py`
- [ ] T012 [US1] Implement Create Company Profile endpoint in `src/controllers/company/create_company_controller.py`
- [ ] T013 [US1] Return user-friendly validation messages in `src/controllers/company/create_company_controller.py`

**Checkpoint**: Marketing organizers can create company profiles.

---

## Phase 4: User Story 2 — Manage Brand Reference Images (Priority: P1)

**Goal**: Allow marketing organizers to upload, replace, retrieve, and remove brand reference images.

**Independent Test**: Upload six images to an existing company profile and verify that all images are associated correctly while rejecting a seventh upload.

### Implementation

- [ ] T014 [US2] Implement Upload Brand Image service in `src/services/company/upload_brand_image_service.py`
- [ ] T015 [P] [US2] Implement Remove Brand Image service in `src/services/company/remove_brand_image_service.py`
- [ ] T016 [P] [US2] Implement Replace Brand Image service in `src/services/company/replace_brand_image_service.py`
- [ ] T017 [US2] Validate uploaded image files in `src/services/company/image_validation_service.py`
- [ ] T018 [US2] Enforce maximum six reference images per company in `src/services/company/image_validation_service.py`
- [ ] T019 [US2] Implement Brand Image management endpoint in `src/controllers/company/brand_image_controller.py`

**Checkpoint**: Marketing organizers can manage brand reference images for company profiles.

---

## Phase 5: User Story 3 — Update Company Profile (Priority: P2)

**Goal**: Allow users to modify existing company information while preserving campaign history.

**Independent Test**: Update company information and verify the latest information is returned without affecting previous campaigns.

### Implementation

- [ ] T020 [US3] Implement Update Company Profile service in `src/services/company/update_company_service.py`
- [ ] T021 [US3] Validate unique company names during update in `src/services/company/company_validation_service.py`
- [ ] T022 [US3] Preserve existing campaign history during updates in `src/services/company/update_company_service.py`
- [ ] T023 [US3] Implement Update Company endpoint in `src/controllers/company/update_company_controller.py`

**Checkpoint**: Company profiles are fully manageable.

---

## Phase 6: User Story 4 — Retrieve Company Profile (Priority: P2)

**Goal**: Allow users and downstream services to retrieve complete company profiles.

**Independent Test**: Retrieve an existing company profile using its identifier and verify all company information is returned.

### Implementation

- [ ] T024 [US4] Implement Get Company Profile service in `src/services/company/get_company_service.py`
- [ ] T025 [US4] Implement List Company Profiles service in `src/services/company/list_company_service.py`
- [ ] T026 [US4] Return complete company information including brand images in `src/services/company/get_company_service.py`
- [ ] T027 [US4] Implement Company retrieval endpoints in `src/controllers/company/company_query_controller.py`

**Checkpoint**: Company profiles are retrievable by identifier.

---

## Phase 7: User Story 5 — Provide Brand Information for Campaign Generation (Priority: P3)

**Goal**: Provide validated company branding information to Campaign Generation.

**Independent Test**: Generate a campaign request and verify that complete brand information is returned when the selected company profile is valid.

### Implementation

- [ ] T028 [US5] Implement Company Profile lookup for Campaign Generation in `src/services/company/company_lookup_service.py`
- [ ] T029 [US5] Prevent incomplete company profiles from being used in campaign generation in `src/services/company/company_lookup_service.py`
- [ ] T030 [US5] Return brand guidelines and reference images to Campaign Generation in `src/services/company/company_lookup_service.py`

**Checkpoint**: Campaign Generation can consume company branding automatically.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finalize business rules, validation, and system reliability.

- [ ] T031 Validate all business rules in `src/services/company/`
- [ ] T032 Improve user-facing validation messages in `src/controllers/company/`
- [ ] T033 Handle concurrent company updates safely in `src/services/company/update_company_service.py`
- [ ] T034 Prevent deletion of company profiles referenced by active campaigns in `src/services/company/delete_company_service.py`
- [ ] T035 Verify all acceptance scenarios defined in `spec.md`
- [ ] T036 Verify all success criteria defined in `spec.md`

**Checkpoint**: Feature complete — all business rules and validation finalized.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Setup
    │
    ▼
Foundational Components
    │
    ├──────────────┐
    ▼              ▼
US1            US2
    │              │
    └──────┬───────┘
           ▼
         US3
           │
           ▼
         US4
           │
           ▼
         US5
           │
           ▼
        Polish
```

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — independent of other stories
- **User Story 2 (Phase 4)**: Depends on Foundational — parallel with US1
- **User Story 3 (Phase 5)**: Depends on US1 + US2 completion
- **User Story 4 (Phase 6)**: Depends on US1 + US2 completion
- **User Story 5 (Phase 7)**: Depends on US3 + US4 completion
- **Polish (Phase 8)**: Depends on all user stories complete

### Within Each User Story

- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

---

## Parallel Execution Opportunities

### Phase 2 (Foundational)

- T005 and T006 can run in parallel (Brand Image entity + Company validation rules)

### Phase 4 (User Story 2)

- T015 and T016 can run in parallel (Remove + Replace Brand Image services)

### Task Parallelism Table

| Parallel Group | Tasks | Files Involved |
|----------------|-------|----------------|
| P1 | T005, T006 | `models/brand_reference_image.py`, `validators/company_validator.py` |
| P2 | T015, T016 | `services/company/remove_brand_image_service.py`, `services/company/replace_brand_image_service.py` |

---

## Implementation Strategy

### MVP

Complete:
- Phase 1 (Setup)
- Phase 2 (Foundational)
- User Story 1 (Create Company Profile)
- User Story 2 (Manage Brand Reference Images)

**Result**: Marketing organizers can create company profiles and manage brand reference images.

---

### Increment 2

Implement:
- User Story 3 (Update Company Profile)
- User Story 4 (Retrieve Company Profile)

**Result**: Company profiles become fully manageable and retrievable.

---

### Increment 3

Implement:
- User Story 5 (Brand Information for Campaign Generation)

**Result**: Campaign Generation can consume company branding automatically.

---

### Final

Complete Phase 8 (Polish).

Validate all acceptance criteria and business rules.

---

## Notes

- **36 tasks total** across 8 phases
- **[P] tasks** = different files, no dependencies — can run in parallel
- **[US*] labels** map tasks to specific user stories for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- File paths follow `backend/src/` conventions per the project structure
