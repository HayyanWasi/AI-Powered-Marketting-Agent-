# Implementation Tasks: Content Validation Service

**Feature**: Content Validation Service  
**Branch**: 008-validation-service  
**Spec File**: specs/008-validation-service/spec.md  

## Overview

Implementation tasks for the Content Validation Service following the project constitution and constitution check requirements. All tasks are organized by user story priority (P1, P2, P3) with independent testability.

## Project Structure Decision

**Selected**: Option 1: Single project structure  
Based on the project being part of the larger AI Social Campaign Manager backend, this follows the established pattern with `src/` and `tests/` directories at the repository root. This enables direct integration with existing campaign generation and validation workflows.

## Dependencies

### Phase 1: Setup

- [ ] T001 [P] Initialize project structure `backend/` with standard Python layout
- [ ] T002 [P] Create `pyproject.toml` with Python 3.13 and dependencies (FastAPI, Pillow, Pydantic v2, Supabase Python SDK)
- [ ] T003 [P] Create `.python-version` file specifying Python 3.13
- [ ] T004 [P] Create `uv.lock` for deterministic dependency management
- [ ] T005 [P] Create initial README.md with project overview and quick start

### Phase 2: Foundational Tasks (Blocking Prerequisites)

- [ ] T006 Initialize FastAPI application `src/main.py`  
- [ ] T007 Create Pydantic models for validation requests/responses in `src/models/validation.py`
- [ ] T008 Create database models (empty as validation uses in-memory results)
- [ ] T009 Create result data structures in `src/models/validation_result.py`
- [ ] T010 Implement environment configuration in `src/config/settings.py`
- [ ] T011 Create basic test infrastructure in `tests/`
- [ ] T012 Configure CI/CD pipeline files (`.github/workflows/`, `Dockerfile`)

## User Story 1: Campaign Validation Initiation (Priority: P1)

**Goal**: When a campaign is generated and a social media platform is selected, automatically validate campaign content before allowing user access to preview.

### Independent Test Criteria:
- Can validate a campaign by providing content and platform selection
- Can verify validation completes before user can proceed to campaign preview
- System blocks preview access for campaigns that fail validation
- System allows preview access only for campaigns that pass validation

### Implementation Tasks:

- [ ] T013 [US1] Create Campaign model `src/models/campaign.py` with fields: id, content, images, platform, created_at, validated_at, validation_status
- [ ] T014 [US1] Create ValidationService `src/services/validation_service.py` with main validation logic
- [ ] T015 [US1] Create Platform enum model `src/models/platform.py` for LinkedIn, Instagram, Facebook
- [ ] T016 [US1] Create ValidationRule model `src/models/validation_rule.py` with platform-specific validation rules
- [ ] T017 [US1] Implement CharacterValidation validator in `src/validators/text_validator.py`
- [ ] T018 [US1] Implement ImageValidation validator in `src/validators/image_validator.py`
- [ ] T019 [US1] Create ValidationGateway in `src/gateways/validation_gateway.py` for coordinating validation process
- [ ] T020 [US1] Implement text validation logic in `src/validators/character_limit_validator.py`
- [ ] T021 [US1] Implement image validation logic in `src/validators/image_resolution_validator.py`
- [ ] T022 [US1] Create API endpoint `src/api/routes/validation.py` with POST /campaigns/{id}/validate
- [ ] T023 [US1] Create API route for preview validation check in `src/api/routes/preview.py`
- [ ] T024 [US1] Create validation controller `src/controllers/validation_controller.py`
- [ ] T025 [US1] Create comprehensive unit tests for validation service in `tests/unit/test_validation_service.py`
- [ ] T026 [US1] Create integration tests for validation flow in `tests/integration/test_validation_integration.py`
- [ ] T027 [US1] Create API endpoint tests in `tests/unit/test_api_endpoints.py`
- [ ] T028 [US1] Create validator tests in `tests/unit/test_validators.py`

## User Story 2: Validation Results Display (Priority: P2)

**Goal**: Provide clear understanding of validation outcomes, including successful validation and specific rule violations that prevent preview access.

### Independent Test Criteria:
- Can validate a campaign and see detailed validation results
- Can verify campaigns that pass validation allow preview
- Can verify campaigns that fail validation block preview
- Clear error messages show specific text rule violations

### Implementation Tasks:

- [ ] T029 [US2] Create ValidationResponse model `src/models/validation_response.py`
- [ ] T030 [US2] Create ValidationResult model `src/models/validation_result.py`
- [ ] T031 [US2] Create TextValidationResult model `src/models/text_validation_result.py`
- [ ] T032 [US2] Create ImageValidationResult model `src/models/image_validation_result.py`
- [ ] T033 [US2] Implement validation result formatter `src/formatters/validation_formatter.py`
- [ ] T034 [US2] Create error message generator `src/utils/error_messages.py`
- [ ] T035 [US2] Implement validation status service `src/services/validation_status_service.py`
- [ ] T036 [US2] Create test data factories in `tests/factories/validation_test_factory.py`
- [ ] T037 [US2] Create validation result display tests in `tests/unit/test_validation_display.py`
- [ ] T038 [US2] Create error message tests in `tests/unit/test_error_messages.py`
- [ ] T039 [US2] Create validation status tests in `tests/unit/test_validation_status_service.py`
- [ ] T040 [US2] Create test scenarios for validation workflows in `tests/integration/test_validation_workflows.py`

## User Story 3: Text and Image Independent Validation (Priority: P3)

**Goal**: Validate text content and image assets independently within a single validation process, with separate rule sets and result reports for each.

### Independent Test Criteria:
- Can provide campaign with both text and image content
- Can verify text and image validation results are reported independently
- Can validate text and image rules simultaneously in same response
- Each component has separate validation status and errors

### Implementation Tasks:

- [ ] T041 [US3] Create ParallelValidationService `src/services/parallel_validation_service.py`
- [ ] T042 [US3] Create TextValidationComponent `src/components/text_validation_component.py`
- [ ] T043 [US3] Create ImageValidationComponent `src/components/image_validation_component.py`
- [ ] T044 [US3] Create IndependentValidationExecutor `src/execution/independent_validation_executor.py`
- [ ] T045 [US3] Create ValidationWorkflowRunner `src/workflows/validation_workflow_runner.py`
- [ ] T046 [US3] Create ComponentResult model `src/models/component_result.py`
- [ ] T047 [US3] Create ParallelValidationTask model `src/models/parallel_validation_task.py`
- [ ] T048 [US3] Create concurrent validation tests in `tests/unit/test_concurrent_validation.py`
- [ ] T049 [US3] Create component integration tests in `tests/integration/test_component_integration.py`
- [ ] T050 [US3] Create workflow execution tests in `tests/unit/test_workflow_execution.py`

## Parallel Execution Examples

### Phase 1 Parallel Tasks (Setup):
- **T001**, **T002**, **T003**, **T004** can run in parallel (all create files without dependencies)
- **T005** can run parallel after **T001-T004**

### User Story 1 Parallel Tasks (US1):
- **T013-T018** can run in parallel (all create models without dependencies)
- **T019** depends on **T013-T018**
- **T020-T021** can run in parallel (both validators, no dependencies)
- **T022** and **T023** can run in parallel (API routes, no dependencies)
- **T024** depends on **T022** and **T023**

### User Story 2 Parallel Tasks (US2):
- **T029-T035** can run in parallel (all create models and services, no dependencies)
- **T036-T038** can run in parallel (test files, no dependencies)
- **T039** depends on **T029-T038**
- **T040** depends on **T029-T039**

### User Story 3 Parallel Tasks (US3):
- **T041, T042, T043** can run in parallel (service and component files, no dependencies)
- **T044, T045** can run in parallel (execution and workflow files, no dependencies)
- **T046, T047** can run in parallel (model files, no dependencies)
- **T048** can run parallel after **T041-T047**
- **T049** depends on **T041-T048**
- **T050** depends on **T041-T049**

## Dependencies Section

### Critical Path
T001 → T002 → T006 → T013 → T014 → T017 → T019 → T022 → T023 → T024 → T028 → T025

### User Story 1 Dependencies
- **Blocking**: T001-T006, T013-T021
- **Parallelizable**: T020-T021, T022-T023

### User Story 2 Dependencies
- **Blocking**: T029-T039
- **Parallelizable**: T029-T035, T036-T038

### User Story 3 Dependencies
- **Blocking**: T041-T050
- **Parallelizable**: T041-T047, T048

## Implementation Strategy

### MVP (Minimum Viable Product)
**Scope**: User Story 1 (Campaign Validation Initiation) only

**MVP Deliverables**:
1. Basic campaign content model
2. Platform enum with supported platforms
3. Character validation rule (LinkedIn, Instagram, Facebook limits)
4. Basic validation service with linear execution
5. API endpoint for validation
6. Preview access control integration
7. Basic error reporting

**Tests for MVP**:
- T013, T015, T017, T020, T022, T025, T027 (core User Story 1 tasks)

### Phase 2: User Story 2 (Validation Results Display)
**Build upon MVP**: 
- Add comprehensive validation response models
- Implement detailed error reporting
- Add validation status tracking
- Create result formatting capabilities

### Phase 3: User Story 3 (Text and Image Independent Validation)
**Enhance**: 
- Add parallel validation execution
- Implement component-based validation
- Add workflow orchestration
- Create comprehensive test scenarios

### Future Enhancements (Phase 4+)
- Advanced image validation (format, size checks)
- Validation rule management
- Performance optimization
- Monitoring and metrics
- Advanced error recovery

## Quality Gates

### Code Quality Requirements
- All new code must have comprehensive type hints
- Every function must have Google-style docstrings
- No print statements - use logging instead
- All edge cases must be handled gracefully
- All validation errors must provide actionable user feedback

### Testing Requirements
- All new code must have unit test coverage >= 80%
- All validation rules must be tested
- All error conditions must be tested
- All API endpoints must have test coverage

### Security Requirements
- No hardcoded sensitive data
- All user input must be validated
- Error messages must not expose system internals
- API authentication must be implemented

### Architecture Requirements
- Linear pipeline processing (KISS principle)
- No RAG or complex dependencies
- Environment variables only for configuration
- Stateless validation services

## Notes

- This implementation follows the project constitution principles for AI Social Campaign Manager
- All validation follows the "Never modify campaign content" principle
- Linear validation pipeline ensures predictable behavior
- Parallel execution where possible for improved performance
- Comprehensive error handling provides user-friendly feedback
- Individual user stories can be implemented and tested independently
- MVP focuses on User Story 1 for rapid delivery