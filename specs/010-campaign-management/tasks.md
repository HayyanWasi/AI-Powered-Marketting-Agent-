---
description: "Task list for Campaign Management Module implementation"
---

# Tasks: Campaign Management Module

**Input**: Design documents from `/specs/010-campaign-management/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Test tasks included for contract and integration testing (recommended per constitution Test-First principle).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to user story from spec.md (US1, US2, US3, US4, US5, US6, US7)
- Exact file paths from plan.md project structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create backend/src directory structure per plan.md (api/routes, models, services, repositories, config, tests)
- [ ] T002 Initialize Python project structure per plan.md (api/routes, models, services, repositories, config, tests/unit, tests/integration)
- [ ] T003 [P] Configure linting (ruff) and formatting (black) in pyproject.toml
- [ ] T004 [P] Configure pytest with pytest-asyncio, pytest-cov in pyproject.toml
- [ ] T005 [P] Add Supabase Python SDK, Pydantic v2, httpx to pyproject.toml dependencies
- [ ] T006 [P] Create .env.example with SUPABASE_URL, SUPABASE_KEY, DATABASE_URL placeholders

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

⚠️ **CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 [P] Create database migration system setup (alembic or supabase CLI migrations)
- [ ] T008 Create migration: campaigns table with all fields, indexes, constraints (data-model.md)
- [ ] T009 Create migration: campaign_history table with append-only trigger (research.md)
- [ ] T010 Create migration: campaign_assets table with indexes (data-model.md)
- [ ] T011 Create migration: campaign_configurations table (if separate from campaigns)
- [ ] T012 [P] Create Supabase async client wrapper in backend/src/config/supabase.py
- [ ] T013 [P] Create settings/configuration in backend/src/config/settings.py (Pydantic Settings)
- [ ] T014 [P] Create base repository class with transaction support in backend/src/repositories/base.py
- [ ] T015 [P] Create Pydantic schemas for requests/responses from contracts/openapi.yaml in backend/src/models/schemas.py
- [ ] T016 [P] Create CampaignState enum in backend/src/models/campaign.py
- [ ] T017 [P] Create Campaign, CampaignHistoryEntry, CampaignAsset dataclasses in backend/src/models/campaign.py
- [ ] T018 [P] Create HistoryEntry dataclass in backend/src/models/history.py
- [ ] T019 [P] Create custom exceptions (StateTransitionError, VersionConflictError, NotFoundError) in backend/src/models/errors.py
- [ ] T020 [P] Create FastAPI app factory and router inclusion in backend/src/main.py
- [ ] T021 [P] Configure CORS, logging middleware, error handlers in backend/src/main.py

**Checkpoint**: Foundation ready - database migrations run, Supabase client works, base models exist, API structure initialized.

---

## Phase 3: User Story 1 - Create a New Campaign (Priority: P1) 🎯 MVP

**Goal**: Allow marketing users to create campaigns with required configuration, persisted in Draft state

**Independent Test**: Create campaign via POST /api/v1/campaigns, verify 201 response, campaign persisted with all fields, state=Draft, unique ID returned

### Tests for User Story 1 (Write FIRST, ensure they FAIL)

- [ ] T022 [P] [US1] Contract test: POST /campaigns creates campaign in Draft state in tests/contract/test_campaigns_create.py
- [ ] T023 [P] [US1] Integration test: Create campaign with valid config, verify persistence in tests/integration/test_campaign_api.py
- [ ] T024 [P] [US1] Integration test: Create campaign with missing required fields returns 400 in tests/integration/test_campaign_api.py
- [ ] T025 [P] [US1] Integration test: Create duplicate name returns 409 in tests/integration/test_campaign_api.py

### Implementation for User Story 1

- [ ] T026 [P] [US1] Implement CampaignRepository.create() with transaction in backend/src/repositories/campaign_repository.py
- [ ] T027 [P] [US1] Implement CampaignRepository.get_by_id() in backend/src/repositories/campaign_repository.py
- [ ] T028 [P] [US1] Implement CampaignRepository.get_by_name() for uniqueness check in backend/src/repositories/campaign_repository.py
- [ ] T029 [US1] Implement CampaignService.create_campaign() with validation in backend/src/services/campaign_service.py
- [ ] T030 [US1] Implement POST /campaigns endpoint in backend/src/api/routes/campaigns.py
- [ ] T031 [US1] Add request validation (Pydantic) for CreateCampaignRequest in backend/src/api/routes/campaigns.py
- [ ] T032 [US1] Add response mapping to CampaignResponse schema in backend/src/api/routes/campaigns.py
- [ ] T033 [US1] Add error handling for validation, duplicate name, database errors in backend/src/api/routes/campaigns.py

**Checkpoint**: User Story 1 fully functional - can create campaigns independently.

---

## Phase 4: User Story 2 - Update Campaign Configuration (Priority: P1)

**Goal**: Allow users to atomically update draft campaign configuration with optimistic locking

**Independent Test**: Update campaign via PUT /api/v1/campaigns/{id} with If-Match header, verify atomic update, version increment, unchanged fields preserved

### Tests for User Story 2 (Write FIRST, ensure they FAIL)

- [ ] T034 [P] [US2] Contract test: PUT /campaigns/{id} updates config atomically in tests/contract/test_campaigns_update.py
- [ ] T035 [P] [US2] Integration test: Partial update preserves unspecified fields in tests/integration/test_campaign_api.py
- [ ] T036 [P] [US2] Integration test: Update non-Draft campaign returns 409 in tests/integration/test_campaign_api.py
- [ ] T037 [P] [US2] Integration test: Version conflict (stale If-Match) returns 409 in tests/integration/test_campaign_api.py
- [ ] T038 [P] [US2] Integration test: Missing If-Match header returns 412 in tests/integration/test_campaign_api.py

### Implementation for User Story 2

- [ ] T039 [P] [US2] Implement CampaignRepository.update() with version check in backend/src/repositories/campaign_repository.py
- [ ] T040 [US2] Implement CampaignService.update_campaign() with atomic update logic in backend/src/services/campaign_service.py
- [ ] T041 [US2] Implement PUT /campaigns/{id} endpoint with If-Match header in backend/src/api/routes/campaigns.py
- [ ] T042 [US2] Add validation: reject if campaign state != Draft in backend/src/services/campaign_service.py
- [ ] T043 [US2] Add ConfigurationChanged history logging in CampaignService.update_campaign() in backend/src/services/campaign_service.py
- [ ] T044 [US2] Add optimistic locking error handling (version conflict → 409) in backend/src/api/routes/campaigns.py

**Checkpoint**: User Story 2 fully functional - can update draft campaigns with atomicity and concurrency control.

---

## Phase 5: User Story 3 - Advance Campaign Through Lifecycle (Priority: P1)

**Goal**: Enforce valid state transitions (Draft→Ready→Review→Approved→Published) with preconditions

**Independent Test**: Transition campaign through all valid states via POST /api/v1/campaigns/{id}/transition, verify each transition recorded in history

### Tests for User Story 3 (Write FIRST, ensure they FAIL)

- [ ] T045 [P] [US3] Contract test: Valid transitions succeed (Draft→Ready→Review→Approved→Published) in tests/contract/test_campaigns_transition.py
- [ ] T046 [P] [US3] Contract test: Invalid transitions rejected with valid next states in tests/contract/test_campaigns_transition.py
- [ ] T047 [P] [US3] Integration test: Draft→Ready requires complete config in tests/integration/test_campaign_api.py
- [ ] T048 [P] [US3] Integration test: Approved→Published requires assets (if configured) in tests/integration/test_campaign_api.py
- [ ] T049 [P] [US3] Integration test: Each transition logs StateTransitioned history entry in tests/integration/test_campaign_api.py
- [ ] T050 [P] [US3] Unit test: State machine validates all valid/invalid transitions in tests/unit/test_state_machine.py

### Implementation for User Story 3

- [ ] T051 [P] [US3] Implement StateMachine class with VALID_TRANSITIONS in backend/src/services/state_machine.py
- [ ] T052 [P] [US3] Implement StateMachine.validate_transition() returning (bool, error_message) in backend/src/services/state_machine.py
- [ ] T053 [P] [US3] Implement StateMachine.get_valid_next_states() in backend/src/services/state_machine.py
- [ ] T054 [US3] Implement CampaignService.transition_campaign() with preconditions in backend/src/services/campaign_service.py
- [ ] T055 [US3] Add transition preconditions: Draft→Ready requires config complete, Approved→Published requires assets in backend/src/services/campaign_service.py
- [ ] T056 [US3] Implement POST /campaigns/{id}/transition endpoint in backend/src/api/routes/campaigns.py
- [ ] T057 [US3] Add StateTransitioned history logging in CampaignService.transition_campaign() in backend/src/services/campaign_service.py
- [ ] T058 [US3] Set published_at timestamp on Approved→Published transition in backend/src/services/campaign_service.py
- [ ] T059 [US3] Add error handling for invalid transitions (409 with valid next states) in backend/src/api/routes/campaigns.py

**Checkpoint**: User Story 3 fully functional - lifecycle enforcement with history logging.

---

## Phase 6: User Story 6 - Retrieve Campaign for Downstream Use (Priority: P1)

**Goal**: Provide public API for downstream modules to read campaign configuration and assets

**Independent Test**: GET /api/v1/campaigns/{id} returns full campaign with assets, works for any state

### Tests for User Story 6 (Write FIRST, ensure they FAIL)

- [ ] T060 [P] [US6] Contract test: GET /campaigns/{id} returns full config + assets in tests/contract/test_campaigns_get.py
- [ ] T061 [P] [US6] Integration test: Retrieve campaign in Draft state works in tests/integration/test_campaign_api.py
- [ ] T062 [P] [US6] Integration test: Non-existent ID returns 404 in tests/integration/test_campaign_api.py

### Implementation for User Story 6

- [ ] T063 [P] [US6] Implement CampaignRepository.get_with_assets() joining assets in backend/src/repositories/campaign_repository.py
- [ ] T064 [US6] Implement CampaignService.get_campaign() in backend/src/services/campaign_service.py
- [ ] T065 [US6] Implement GET /campaigns/{id} endpoint in backend/src/api/routes/campaigns.py
- [ ] T066 [US6] Add CampaignResponse mapping with nested assets in backend/src/api/routes/campaigns.py

**Checkpoint**: User Story 6 fully functional - downstream modules can retrieve campaigns.

---

## Phase 7: User Story 4 - Archive and Restore Campaign (Priority: P2)

**Goal**: Archive campaigns from any state, restore to previous state

**Independent Test**: Archive published campaign → excluded from active lists → restore → returns to Published state

### Tests for User Story 4 (Write FIRST, ensure they FAIL)

- [ ] T067 [P] [US4] Contract test: POST /campaigns/{id}/archive works from any state in tests/contract/test_campaigns_archive.py
- [ ] T068 [P] [US4] Contract test: POST /campaigns/{id}/restore returns to previous state in tests/contract/test_campaigns_restore.py
- [ ] T069 [P] [US4] Integration test: Archived campaigns excluded from default list in tests/integration/test_campaign_api.py
- [ ] T070 [P] [US4] Integration test: Archive logs Archived history, Restore logs Restored history in tests/integration/test_campaign_api.py
- [ ] T071 [P] [US4] Integration test: Restore non-archived campaign returns 409 in tests/integration/test_campaign_api.py

### Implementation for User Story 4

- [ ] T072 [P] [US4] Implement CampaignRepository.archive() storing previous_state in backend/src/repositories/campaign_repository.py
- [ ] T073 [P] [US4] Implement CampaignRepository.restore() restoring previous_state in backend/src/repositories/campaign_repository.py
- [ ] T074 [US4] Implement CampaignService.archive_campaign() with Archived history logging in backend/src/services/campaign_service.py
- [ ] T075 [US4] Implement CampaignService.restore_campaign() with Restored history logging in backend/src/services/campaign_service.py
- [ ] T076 [US4] Implement POST /campaigns/{id}/archive endpoint in backend/src/api/routes/campaigns.py
- [ ] T077 [US4] Implement POST /campaigns/{id}/restore endpoint in backend/src/api/routes/campaigns.py
- [ ] T078 [US4] Set archived_at timestamp on archive, clear on restore in backend/src/services/campaign_service.py
- [ ] T079 [US4] Add archived filter to list campaigns (default exclude) in backend/src/services/campaign_service.py

**Checkpoint**: User Story 4 fully functional - archive/restore with history.

---

## Phase 8: User Story 5 - View Campaign History (Priority: P2)

**Goal**: Provide paginated, immutable history of all campaign events

**Independent Test**: GET /api/v1/campaigns/{id}/history returns paginated events in chronological order with all details

### Tests for User Story 5 (Write FIRST, ensure they FAIL)

- [ ] T080 [P] [US5] Contract test: GET /campaigns/{id}/history returns paginated entries in tests/contract/test_campaigns_history.py
- [ ] T081 [P] [US5] Integration test: History includes all event types in order in tests/integration/test_campaign_api.py
- [ ] T082 [P] [US5] Integration test: Publication events include snapshot in tests/integration/test_campaign_api.py
- [ ] T083 [P] [US5] Integration test: History immutability - UPDATE/DELETE rejected in tests/integration/test_history_immutability.py

### Implementation for User Story 5

- [ ] T084 [P] [US5] Implement HistoryRepository.get_by_campaign() with pagination in backend/src/repositories/history_repository.py
- [ ] T085 [US5] Implement HistoryService.get_history() in backend/src/services/history_service.py
- [ ] T086 [US5] Implement GET /campaigns/{id}/history endpoint in backend/src/api/routes/campaigns.py
- [ ] T087 [US5] Add HistoryEntryResponse mapping with all fields in backend/src/api/routes/campaigns.py

**Checkpoint**: User Story 5 fully functional - complete immutable history with pagination.

---

## Phase 9: User Story 7 - Store Campaign Assets (Priority: P2)

**Goal**: Associate assets (copy, images, hashtags, metadata) with campaigns regardless of source

**Independent Test**: POST /api/v1/campaigns/{id}/assets adds asset, GET returns all assets with campaign

### Tests for User Story 7 (Write FIRST, ensure they FAIL)

- [ ] T088 [P] [US7] Contract test: POST /campaigns/{id}/assets creates asset in tests/contract/test_campaigns_assets.py
- [ ] T089 [P] [US7] Contract test: GET /campaigns/{id}/assets lists all assets in tests/contract/test_campaigns_assets.py
- [ ] T090 [P] [US7] Integration test: Assets from AI/manual/imported stored identically in tests/integration/test_campaign_api.py
- [ ] T091 [P] [US7] Integration test: Asset content structure varies by type (copy/image/hashtag) in tests/integration/test_campaign_api.py

### Implementation for User Story 7

- [ ] T092 [P] [US7] Implement AssetRepository.create() in backend/src/repositories/asset_repository.py
- [ ] T093 [P] [US7] Implement AssetRepository.get_by_campaign() in backend/src/repositories/asset_repository.py
- [ ] T094 [US7] Implement AssetService.create_asset() with type validation in backend/src/services/asset_service.py
- [ ] T095 [US7] Implement AssetService.list_assets() in backend/src/services/asset_service.py
- [ ] T096 [US7] Implement POST /campaigns/{id}/assets endpoint in backend/src/api/routes/campaigns.py
- [ ] T097 [US7] Implement GET /campaigns/{id}/assets endpoint in backend/src/api/routes/campaigns.py
- [ ] T098 [US7] Add AssetAssociated history logging in AssetService.create_asset() in backend/src/services/asset_service.py

**Checkpoint**: User Story 7 fully functional - asset management decoupled from generation source.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories

- [ ] T099 [P] Add comprehensive unit tests for state machine (100% transition coverage) in tests/unit/test_state_machine.py
- [ ] T100 [P] Add unit tests for history service immutability in tests/unit/test_history_service.py
- [ ] T101 [P] Add unit tests for campaign model validation in tests/unit/test_campaign_model.py
- [ ] T102 [P] Run quickstart.md curl commands as integration validation script
- [ ] T103 Performance test: Campaign CRUD <100ms p95 in tests/performance/test_campaign_perf.py
- [ ] T104 Performance test: History query <1s for 500 entries in tests/performance/test_history_perf.py
- [ ] T105 Performance test: Campaign listing <500ms for 10k campaigns in tests/performance/test_list_perf.py
- [ ] T106 [P] Add OpenAPI documentation comments to all endpoints in backend/src/api/routes/campaigns.py
- [ ] T107 [P] Add Google-style docstrings to all public functions in services/repositories
- [ ] T108 [P] Verify 80%+ code coverage with pytest-cov
- [ ] T109 [P] Add database indexes for query optimization (per data-model.md)
- [ ] T110 [P] Add health check endpoint for campaign service
- [ ] T111 Run ruff check and black format on all new code
- [ ] T112 Run mypy type checking on backend/src

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - **BLOCKS all user stories**
- **User Stories (Phases 3-9)**: All depend on Foundational completion
  - US1, US2, US3, US6 (P1) can run in parallel after Foundational
  - US4, US5, US7 (P2) can run in parallel after Foundational
- **Polish (Phase 10)**: Depends on all desired user stories complete

### User Story Dependencies

| Story | Priority | Depends On | Can Start After |
|-------|----------|------------|-----------------|
| US1 Create Campaign | P1 | Foundational | Phase 2 complete |
| US2 Update Config | P1 | Foundational, US1 (uses Campaign model) | Phase 2 complete |
| US3 Lifecycle Transitions | P1 | Foundational, US1, US2 (uses state machine) | Phase 2 complete |
| US6 Retrieve for Downstream | P1 | Foundational, US1 | Phase 2 complete |
| US4 Archive/Restore | P2 | Foundational, US1, US3 | Phase 2 complete |
| US5 View History | P2 | Foundational, US1, US3 | Phase 2 complete |
| US7 Store Assets | P2 | Foundational, US1 | Phase 2 complete |

### Within Each User Story

1. Tests (contract + integration) → **MUST FAIL first**
2. Models/Enums →
3. Repositories →
4. Services →
5. API Endpoints →
6. Integration/Validation

---

## Parallel Execution Examples

### After Foundational (Phase 2) Complete - All P1 Stories in Parallel:

```bash
# Developer A: User Story 1
Task: T022-T033 [US1] Create Campaign

# Developer B: User Story 2
Task: T034-T044 [US2] Update Campaign Config

# Developer C: User Story 3
Task: T045-T059 [US3] Lifecycle Transitions

# Developer D: User Story 6
Task: T060-T066 [US6] Retrieve Campaign
```

### Within a User Story - Models in Parallel:

```bash
# For US1:
Task: T026 [P] [US1] CampaignRepository.create()
Task: T027 [P] [US1] CampaignRepository.get_by_id()
Task: T028 [P] [US1] CampaignRepository.get_by_name()
```

### Tests in Parallel (per story):

```bash
# For US3:
Task: T045 [P] [US3] Contract test valid transitions
Task: T046 [P] [US3] Contract test invalid transitions
Task: T047 [P] [US3] Integration test Draft→Ready preconditions
Task: T048 [P] [US3] Integration test Approved→Published preconditions
Task: T049 [P] [US3] Integration test history logging
Task: T050 [P] [US3] Unit test state machine
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test US1 independently with quickstart.md
5. Deploy/demo MVP

### Incremental Delivery

1. Foundation ready → US1 working → **Deploy MVP**
2. Add US2 → Test independently → Deploy
3. Add US3 → Test independently → Deploy
4. Add US6 → Test independently → Deploy
5. Add US4, US5, US7 (P2) → Test → Deploy
6. Phase 10: Polish all

### Parallel Team Strategy

With multiple developers:
1. Team completes Setup + Foundational together
2. Once Foundational done, assign each P1 story to a developer
3. Stories integrate independently via shared foundation
4. P2 stories can start as P1 stories complete

---

## Total Task Count: 112

- Setup: 6 tasks
- Foundational: 14 tasks
- US1 (Create): 12 tasks
- US2 (Update): 11 tasks
- US3 (Lifecycle): 15 tasks
- US6 (Retrieve): 7 tasks
- US4 (Archive): 12 tasks
- US5 (History): 8 tasks
- US7 (Assets): 11 tasks
- Polish: 14 tasks

---

## Notes

- All tasks use exact file paths from plan.md project structure
- [P] tasks can run in parallel (different files, no dependencies)
- [USx] labels enable traceability to user stories
- Test tasks included per constitution Test-First principle (Principle I)
- Each user story is independently testable per spec.md "Independent Test" criteria
- MVP = User Story 1 only (create campaign in Draft state)