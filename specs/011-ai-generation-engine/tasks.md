# Tasks: AI Generation Engine Module

**Input**: plan.md, spec.md

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `backend/src/`, `tests/` at repository root
- **Module structure**: `backend/src/modules/ai_generation/interfaces/`, `backend/src/modules/ai_generation/services/`, `backend/src/modules/ai_generation/models/`
- **Tests**: `backend/tests/unit/modules/ai_generation/` for unit tests, `backend/tests/integration/` for integration tests

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create module structure per implementation plan
- [ ] T002 Initialize Python project with FastAPI dependencies
- [ ] T003 [P] Create module package structure
- [ ] T004 [P] Initialize package configurations (pyproject.toml, ruff, mypy)
- [ ] T005 [P] Create basic CI/CD workflow configuration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 [P] Initialize FastAPI project structure
- [ ] T007 [P] Configure database connection pool (conceptual implementation)
- [ ] T008 [P] Setup logging and error handling framework
- [ ] T009 [P] Create base models and validation schemas
- [ ] T010 [P] Initialize main application entry point
- [ ] T011 [P] Setup API routing structure
- [ ] T012 [P] Create module interface files
- [ ] T013 [P] Initialize test configuration and fixtures

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Generate Complete Campaign (Priority: P1) 🎯 MVP

**Goal**: Module users can generate a complete marketing campaign (strategy, copy, images) from a single input context.

**Independent Test**: Provide valid generation context and verify that strategy, copy (3 platforms), and images are produced in correct pipeline order.

### Tests for User Story 1

- [ ] T014 [P] [US1] Contract test for complete campaign generation endpoint in tests/integration/test_ai_generation_full_pipeline.py
- [ ] T015 [P] [US1] Integration test for generation pipeline in tests/integration/test_ai_generation_full_pipeline.py
- [ ] T016 [P] [US1] Unit test for ContextBuilder service in backend/tests/unit/modules/ai_generation/test_context_builder.py

### Implementation for User Story 1

- [ ] T017 [P] [US1] Implement Context Builder interface in backend/src/modules/ai_generation/interfaces/context_builder.py
- [ ] T018 [US1] Implement Context Builder service in backend/src/modules/ai_generation/services/context_builder_service.py
- [ ] T019 [US1] Implement Strategy Planner service in backend/src/modules/ai_generation/services/strategy_planner_service.py
- [ ] T020 [US1] Implement Copy Generator service in backend/src/modules/ai_generation/services/llm_service.py
- [ ] T021 [US1] Implement Image Prompt service in backend/src/modules/ai_generation/services/image_prompt_service.py
- [ ] T022 [US1] Implement Image Generator service in backend/src/modules/ai_generation/services/image_generator_service.py
- [ ] T023 [US1] Implement Validation service in backend/src/modules/ai_generation/services/validation_service.py
- [ ] T024 [US1] Create generation context model in backend/src/modules/ai_generation/models/generation_context.py
- [ ] T025 [US1] Create strategy artifact model in backend/src/modules/ai_generation/models/strategy_artifact.py
- [ ] T026 [US1] Create validation artifact model in backend/src/modules/ai_generation/models/validation_artifact.py
- [ ] T027 [P] [US1] Create API endpoint for full campaign generation in backend/src/api/routes/ai_generation.py
- [ ] T028 [US1] Create domain models and utility classes in backend/src/modules/ai_generation/models/
- [ ] T029 [US1] Create business logic for campaign generation in backend/src/modules/ai_generation/services/ai_generation_service.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Regenerate Copy (Priority: P2)

**Goal**: Module users can regenerate text content while preserving approved strategy and existing images.

**Independent Test**: Provide existing Strategy Artifact and verify only Copy Artifact changes.

### Tests for User Story 2

- [ ] T030 [P] [US2] Test text-only regeneration functionality in backend/tests/unit/modules/ai_generation/test_copy_regeneration.py
- [ ] T031 [P] [US2] Test text regeneration without changes in backend/tests/unit/modules/ai_generation/test_copy_regeneration.py
- [ ] T032 [P] [US2] Test text regeneration with new instructions in backend/tests/unit/modules/ai_generation/test_copy_regeneration.py

### Implementation for User Story 2

- [ ] T033 [P] [US2] Implement copy generator copy regeneration logic in backend/src/modules/ai_generation/services/llm_service.py
- [ ] T034 [US2] Implement copy regeneration API endpoint in backend/src/api/routes/ai_generation.py
- [ ] T035 [US2] Test strategy preservation during text regeneration in backend/tests/unit/modules/ai_generation/test_strategy_preservation.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Regenerate Image (Priority: P2)

**Goal**: Module users can regenerate images while preserving approved strategy and existing copy.

**Independent Test**: Provide Strategy and Copy Artifacts and verify only Image Prompt and Image Artifacts change.

### Tests for User Story 3

- [ ] T036 [P] [US3] Test image-only regeneration functionality in backend/tests/unit/modules/ai_generation/test_image_regeneration.py
- [ ] T037 [P] [US3] Test image regeneration without changes in backend/tests/unit/modules/ai_generation/test_image_regeneration.py
- [ ] T038 [P] [US3] Test image regeneration with new preferences in backend/tests/unit/modules/ai_generation/test_image_regeneration.py

### Implementation for User Story 3

- [ ] T039 [P] [US3] Implement image prompt editor regenerate logic in backend/src/modules/ai_generation/services/image_prompt_service.py
- [ ] T040 [P] [US3] Implement image generator regenerate logic in backend/src/modules/ai_generation/services/image_generator_service.py
- [ ] T041 [US3] Test strategy preservation during image regeneration in backend/tests/unit/modules/ai_generation/test_strategy_preservation.py
- [ ] T042 [US3] Test copy preservation during image regeneration in backend/tests/unit/modules/ai_generation/test_copy_preservation.py

**Checkpoint**: At this point, User Stories 1, 2 AND 3 should all be independently functional

---

## Phase 6: User Story 4 - Revise Campaign Strategy (Priority: P3)

**Goal**: Module users can revise campaign strategy and automatically regenerate all dependent artifacts.

**Independent Test**: Provide updated Generation Context and verify a new Strategy Artifact and dependent artifacts are generated.

### Tests for User Story 4

- [ ] T043 [P] [US4] Test strategy revision with new campaign goals in backend/tests/unit/modules/ai_generation/test_strategy_recreation.py
- [ ] T044 [P] [US4] Test full regeneration without strategy changes in backend/tests/unit/modules/ai_generation/test_strategy_revision.py
- [ ] T045 [P] [US4] Test strategy revision validation in backend/tests/unit/modules/ai_generation/test_strategy_validation.py

### Implementation for User Story 4

- [ ] T046 [P] [US4] Implement strategy revision generation logic in backend/src/modules/ai_generation/services/strategy_planner_service.py
- [ ] T047 [US4] Implement strategy revision API endpoint in backend/src/api/routes/ai_generation.py
- [ ] T048 [US4] Test strategy dependency regeneration in backend/tests/unit/modules/ai_generation/test_strategy_dependencies.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Intent Analysis

**Purpose**: Detect user modification intent for smart regeneration routing

- [ ] T049 Implement Intent Analyzer in backend/src/modules/ai_generation/services/intent_analyzer.py
- [ ] T050 Implement intent routing logic in backend/src/modules/ai_generation/services/ai_generation_service.py
- [ ] T051 [P] Implement intent detection algorithms in backend/src/modules/ai_generation/services/intent_analyzer.py
- [ ] T052 Test intent analysis with various inputs in backend/tests/unit/modules/ai_generation/test_intent_analysis.py

---

## Phase 8: Public Service

**Purpose**: Expose the module's public generation capabilities through service APIs

- [ ] T053 Implement generate() service in backend/src/modules/ai_generation/services/ai_generation_service.py
- [ ] T054 Implement regenerate_text() service in backend/src/modules/ai_generation/services/ai_generation_service.py
- [ ] T055 Implement regenerate_image() service in backend/src/modules/ai_generation/services/ai_generation_service.py
- [ ] T056 [P] Create service layer for public API in backend/src/modules/ai_generation/services/ai_generation_service.py

---

## Phase 9: Integration & Documentation

**Purpose**: End-to-end pipeline testing and documentation

- [ ] T057 End-to-end generation pipeline test in backend/tests/integration/test_ai_generation_full_pipeline.py
- [ ] T058 Integration tests for all scenarios in backend/tests/integration/test_ai_generation_full_pipeline.py
- [ ] T059 Failure scenario tests in backend/tests/integration/test_ai_generation_failure.py
- [ ] T060 Create module documentation in docs/ (API reference, usage guide)
- [ ] T061 Update README with module information and usage instructions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phases)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for complete campaign generation endpoint in tests/integration/test_ai_generation_full_pipeline.py"
Task: "Integration test for generation pipeline in tests/integration/test_ai_generation_full_pipeline.py"
Task: "Unit test for ContextBuilder service in backend/tests/unit/modules/ai_generation/test_context_builder.py"

# Launch all models for User Story 1 together:
Task: "Implement Context Builder interface in backend/src/modules/ai_generation/interfaces/context_builder.py"
Task: "Implement Context Builder service in backend/src/modules/ai_generation/services/context_builder_service.py"
Task: "Implement Strategy Planner service in backend/src/modules/ai_generation/services/strategy_planner_service.py"

# Launch all services for User Story 1 together:
Task: "Implement Copy Generator service in backend/src/modules/ai_generation/services/llm_service.py"
Task: "Implement Image Prompt service in backend/src/modules/ai_generation/services/image_prompt_service.py"
Task: "Implement Image Generator service in backend/src/modules/ai_generation/services/image_generator_service.py"
Task: "Implement Validation service in backend/src/modules/ai_generation/services/validation_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
   - Developer D: User Story 4
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

**CRITICAL CHECKPOINTS**: 

- End of Phase 2: All setup and foundational tasks complete
- End of Phase 3: User Story 1 independently functional
- End of Phase 4: User Stories 1 AND 2 independently functional
- End of Phase 5: User Stories 1, 2 AND 3 independently functional

All stories can be delivered incrementally while maintaining module independence and testability.