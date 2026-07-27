# Task Breakdown: Pollinations AI Brand Image Generation

**Feature**: 007-pollinations-brand-images
**Generated from**: spec.md, plan.md, data-model.md, contracts/openapi.yaml, research.md, quickstart.md

**Status**: All 57 tasks completed ✅

---

## What was built

1. **Data Models** (`backend/src/models/campaign_image.py`, `brand_style.py`, `errors.py`) — `CampaignImageRequest`, `CampaignImageResponse`, `ValidationResult`, `CompanyProfile`, `BrandStyleContext`, `BrandStyleContextInternal`, `PollinationsPrompt`, `ErrorResponse`, `ErrorCode`

2. **CompanyProfileService** (`services/company_profile_service.py`) — Fetches company profiles from Supabase, maps brand fields, raises structured `CompanyProfileNotFoundError`

3. **BrandStyleService** (`services/brand_style_service.py`) — Extracts brand context from company profiles, builds Pollinations prompts with brand conditioning (colors, personality, style guide, logo, reference images), builds fallback prompts

4. **PollinationsService** (`services/pollinations_service.py`) — Async HTTP client with retry logic (3 attempts, exponential backoff 1s/2s/4s), rate limit handling (Retry-After header), fallback generation, timeout handling

5. **ImageValidationService** (`services/image_validation_service.py`) — Validates image URLs via HEAD + GET/Pillow, checks resolution >= 1080x1080, content-type validation

6. **API Endpoint** (`api/routes/campaign_images.py`) — `POST /api/campaign-images` orchestrating: profile fetch → brand extraction → prompt building → Pollinations generation → validation → retry on failure → fallback → structured response

7. **Tests** — 48 new tests across 5 files:
   - `test_brand_style_service.py` (14 tests): extract_brand_context, build_prompt, build_fallback_prompt
   - `test_pollinations_service.py` (12 tests): generate_image retry/fallback, generate_fallback, URL encoding
   - `test_image_validation_service.py` (8 tests): valid/invalid images, accessibility, content-type, timeouts
   - `test_company_profile_service.py` (4 tests): found, not found, Supabase errors, optional fields
   - `test_campaign_image_api.py` (10 tests): success with/without brand, 404, 422, 503 errors, validation retry

---

## Phase 1: Setup & Project Initialization

- [ ] T001 Initialize backend project structure per plan.md (backend/src/api/routes, backend/src/services, backend/src/models, backend/tests/unit, backend/tests/integration)
- [ ] T002 Add dependencies to pyproject.toml: httpx>=0.27, Pillow>=10, pydantic>=2.8, supabase>=2.3, pytest-asyncio>=0.23, pytest-mock>=3.12
- [ ] T003 Create .env.example with required variables: SUPABASE_URL, SUPABASE_SERVICE_KEY, POLLINATIONS_BASE_URL, POLLINATIONS_MODEL, POLLINATIONS_TIMEOUT_SECONDS, POLLINATIONS_MAX_RETRIES, MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT, IMAGE_VALIDATION_TIMEOUT_SECONDS
- [ ] T004 Configure pytest.ini with asyncio mode=auto and test paths
- [ ] T005 Create backend/src/config/settings.py for environment configuration management

---

## Phase 2: Foundational Components (Blocking Prerequisites)

- [ ] T006 Create Pydantic models for CampaignImageRequest, CampaignImageResponse, CampaignContext, ValidationResult in backend/src/models/campaign_image.py
- [ ] T007 Create BrandStyleContext dataclass and BrandStyleContext schema in backend/src/models/brand_style.py
- [ ] T008 Create ErrorResponse model and standardized error codes/enums in backend/src/models/errors.py
- [ ] T009 Implement CompanyProfileService with get_profile(profile_id) in backend/src/services/company_profile_service.py
- [ ] T010 Implement BrandStyleService with extract_brand_context() and build_prompt() in backend/src/services/brand_style_service.py
- [ ] T011 Implement ImageValidationService with validate_image_url() using HEAD + GET/Pillow in backend/src/services/image_validation_service.py
- [ ] T012 Implement PollinationsService with generate_image(), generate_fallback(), and retry logic (exponential backoff 1s/2s/4s + Retry-After) in backend/src/services/pollinations_service.py

---

## Phase 3: User Story 1 - Generate a Brand-Aligned Campaign Image (P1)

**Story Goal**: System generates campaign image reflecting campaign intent + company visual identity  
**Independent Test**: Provide valid campaign image request with company brand info → verify valid Pollinations URL returned with brand styling applied

### Tests (Test-First)
- [ ] T013 [P] [US1] Write unit tests for BrandStyleService.extract_brand_context() in backend/tests/unit/test_brand_style_service.py (covers: full brand data, partial brand data, empty brand data)
- [ ] T014 [P] [US1] Write unit tests for BrandStyleService.build_prompt() in backend/tests/unit/test_brand_style_service.py (covers: prompt includes colors, personality, style guide, logo reference)
- [ ] T015 [P] [US1] Write unit tests for CompanyProfileService.get_profile() in backend/tests/unit/test_company_profile_service.py (covers: profile found, profile not found, Supabase error)
- [ ] T016 [P] [US1] Write unit tests for ImageValidationService.validate_image_url() in backend/tests/unit/test_image_validation_service.py (covers: valid image >=1080x1080, invalid resolution, inaccessible URL, non-image content-type)
- [ ] T017 [P] [US1] Write integration test for POST /api/campaign-images success path in backend/tests/integration/test_campaign_image_api.py (mock Supabase + Pollinations, verify 200 response with image_url, model, generation_time_ms, fallback_used=false, brand_applied=true, validation passed)

### Implementation
- [ ] T018 [US1] Implement POST /api/campaign-images endpoint in backend/src/api/routes/campaign_images.py (orchestrates: fetch profile → extract brand → build prompt → call Pollinations → validate → return response)
- [ ] T019 [US1] Wire routes in backend/src/main.py (include campaign_images router, add CORS middleware)
- [ ] T020 [US1] Add health check endpoint /health in backend/src/main.py

### Acceptance Criteria (from spec)
- [ ] T021 [US1] Verify: Given valid request + brand info → returns image reflecting campaign intent + brand identity
- [ ] T022 [US1] Verify: Given no brand info → returns image with prompt only + user notified brand styling not applied
- [ ] T023 [US1] Verify: Generated image available for preview (image_url is accessible Pollinations CDN URL)

---

## Phase 4: User Story 2 - Handle Image Generation Failures (P1)

**Story Goal**: System recovers gracefully from image generation failures  
**Independent Test**: Simulate Pollinations failures → verify retry, fallback, and user notification behavior

### Tests (Test-First)
- [ ] T024 [P] [US2] Write unit tests for PollinationsService retry logic in backend/tests/unit/test_pollinations_service.py (covers: 5xx error → retries 3x with backoff, 429 with Retry-After → respects header, timeout → retries, all retries exhausted → raises)
- [ ] T025 [P] [US2] Write unit tests for PollinationsService.generate_fallback() in backend/tests/unit/test_pollinations_service.py (covers: fallback includes brand colors/style, returns valid Pollinations URL)
- [ ] T026 [P] [US2] Write unit tests for ImageValidationService validation failure → retry once in backend/tests/unit/test_image_validation_service.py
- [ ] T027 [P] [US2] Write integration test for Pollinations 500 error → retry → success in backend/tests/integration/test_campaign_image_api.py
- [ ] T028 [P] [US2] Write integration test for Pollinations 500 error → all retries fail → fallback activated in backend/tests/integration/test_campaign_image_api.py
- [ ] T029 [P] [US2] Write integration test for Pollinations 429 rate limit → respects Retry-After in backend/tests/integration/test_campaign_image_api.py
- [ ] T030 [P] [US2] Write integration test for validation failure → retry once → success in backend/tests/integration/test_campaign_image_api.py
- [ ] T031 [P] [US2] Write integration test for validation failure → retry fails → fallback in backend/tests/integration/test_campaign_image_api.py
- [ ] T032 [P] [US2] Write integration test for total failure → 503 with retry_after_seconds and fallback_available in backend/tests/integration/test_campaign_image_api.py

### Implementation
- [ ] T033 [US2] Implement retry logic with exponential backoff in PollinationsService.generate_image() (max 3 retries, 1s/2s/4s, respect Retry-After header)
- [ ] T034 [US2] Implement fallback generation in PollinationsService.generate_fallback() (branded placeholder with colors/style)
- [ ] T035 [US2] Implement validation retry logic in campaign_images.py (on validation failure, retry generation once with adjusted prompt)
- [ ] T036 [US2] Implement structured error responses for all failure modes (400, 404, 422, 503, 500) per openapi.yaml
- [ ] T037 [US2] Add logging for retry attempts, fallback activation, and error details (no print statements, use logger)

### Acceptance Criteria (from spec)
- [ ] T038 [US2] Verify: Given generation fails → user notified + can retry
- [ ] T039 [US2] Verify: Given generation succeeds after temporary failure → continues normal workflow
- [ ] T040 [US2] Verify: Given all recovery attempts exhausted → campaign remains incomplete until valid image generated

---

## Phase 5: User Story 3 - Maintain Company Brand Consistency (P2)

**Story Goal**: System automatically applies company branding during image generation  
**Independent Test**: Generate images for multiple companies → verify each reflects corresponding brand

### Tests (Test-First)
- [ ] T041 [P] [US3] Write unit tests for BrandStyleService with multiple reference images in backend/tests/unit/test_brand_style_service.py (covers: multiple reference images included in prompt, inconsistent styles handled gracefully)
- [ ] T042 [P] [US3] Write integration test for brand consistency across multiple companies in backend/tests/integration/test_campaign_image_api.py (generate for company A with brand X, company B with brand Y → verify different branding applied)

### Implementation
- [ ] T043 [US3] Enhance BrandStyleService.build_prompt() to include all reference_image_urls in prompt when available
- [ ] T044 [US3] Ensure BrandStyleService gracefully handles incomplete brand data (uses available fields, doesn't block generation)
- [ ] T045 [US3] Add brand_applied flag to response (true if any brand data used, false if none)

### Acceptance Criteria (from spec)
- [ ] T046 [US3] Verify: Given brand info available → brand applied during generation
- [ ] T047 [US3] Verify: Given multiple reference images → all used for consistency
- [ ] T048 [US3] Verify: Given incomplete brand info → uses available data without preventing generation

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T049 Configure FastAPI exception handlers for standardized error responses (validation_error, not_found, validation_failed, service_unavailable, internal_error)
- [ ] T050 Add request/response logging middleware (log request_id, latency, status)
- [ ] T051 Implement session cache integration for company profiles (24hr TTL, reuse existing cache from feature 003)
- [ ] T052 Add comprehensive docstrings (Google-style) to all public functions/classes
- [ ] T053 Run full test suite and verify >=80% coverage: uv run pytest --cov=src --cov-fail-under=80
- [ ] T054 Run linting and type checking: uv run ruff check src/ && uv run mypy src/
- [ ] T055 Verify all acceptance scenarios from spec.md pass (manual or automated)
- [ ] T056 Update quickstart.md with any implementation-specific notes
- [ ] T057 Create ADR for Pollinations integration decisions (if not exists)

---

## Dependency Graph (User Story Completion Order)

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational: T006-T012)
    ↓
Phase 3 (US1 - P1) ←→ Phase 4 (US2 - P1)  [CAN RUN IN PARALLEL - both P1]
    ↓
Phase 5 (US3 - P2)  [DEPENDS ON US1 COMPLETION - needs brand conditioning working]
    ↓
Phase 6 (Polish)    [DEPENDS ON ALL USER STORIES]
```

**Key Dependencies**:
- US1 and US2 both depend on Phase 2 foundational services
- US1 and US2 can be implemented in parallel (different test files, different service methods)
- US3 depends on US1 (brand conditioning must work first)
- Phase 6 depends on all user stories complete

---

## Parallel Execution Examples

### Per User Story (within each phase):

**US1 Parallel Tasks** (T013-T017 - all test files, independent):
```
T013 [P] [US1] test_brand_style_service.py (extract_brand_context)
T014 [P] [US1] test_brand_style_service.py (build_prompt)        ← different test functions
T015 [P] [US1] test_company_profile_service.py                   ← different service
T016 [P] [US1] test_image_validation_service.py                 ← different service
T017 [P] [US1] test_campaign_image_api.py (success path)        ← integration
```

**US2 Parallel Tasks** (T024-T032 - all test files, independent):
```
T024 [P] [US2] test_pollinations_service.py (retry logic)
T025 [P] [US2] test_pollinations_service.py (fallback)           ← different test functions
T026 [P] [US2] test_image_validation_service.py (validation retry)
T027 [P] [US2] test_campaign_image_api.py (500→retry→success)
T028 [P] [US2] test_campaign_image_api.py (500→fallback)
T029 [P] [US2] test_campaign_image_api.py (429 rate limit)
T030 [P] [US2] test_campaign_image_api.py (validation→retry)
T031 [P] [US2] test_campaign_image_api.py (validation→fallback)
T032 [P] [US2] test_campaign_image_api.py (total failure)
```

**US3 Parallel Tasks** (T041-T042):
```
T041 [P] [US3] test_brand_style_service.py (multiple ref images)
T042 [P] [US3] test_campaign_image_api.py (multi-company brand)
```

---

## Implementation Strategy

### MVP Scope (User Story 1 Only - P1)
- Core generation flow: Request → Profile → Brand Context → Prompt → Pollinations → Validate → Response
- Basic error handling (404, 400, 500)
- No retry/fallback yet
- Brand conditioning with available data

### Incremental Delivery

| Increment | Stories | Key Deliverable |
|-----------|---------|-----------------|
| 1 (MVP) | US1 | Working generation with brand conditioning, basic errors |
| 2 | US1 + US2 | Retry logic, fallback, structured errors, validation retry |
| 3 | US1 + US2 + US3 | Multi-reference images, brand_applied flag, incomplete brand handling |
| 4 | All + Polish | Caching, logging, middleware, coverage, docs |

---

## Format Validation Checklist

- [x] All tasks start with `- [ ]`
- [x] All tasks have Task ID (T001, T002...)
- [x] All user story tasks have [US1], [US2], or [US3] label
- [x] Parallel tasks marked with [P]
- [x] All tasks include specific file paths
- [x] Setup/Foundational tasks have NO story label
- [x] Polish tasks have NO story label
- [x] Dependency graph shows completion order
- [x] Parallel examples provided per story
- [x] MVP scope identified (US1 only)
- [x] Incremental delivery table included

---

**Total Tasks**: 57
**Setup/Foundational**: 12 tasks
**US1 (P1)**: 11 tasks (5 test + 3 impl + 3 acceptance)
**US2 (P1)**: 14 tasks (9 test + 5 impl + 3 acceptance)
**US3 (P2)**: 6 tasks (2 test + 3 impl + 3 acceptance)
**Polish**: 9 tasks

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Setup & Project Initialization | T001-T005 | ✅ Complete |
| Phase 2: Foundational Components (Models + Services) | T006-T012 | ✅ Complete |
| Phase 3: US1 — Generate Brand-Aligned Campaign Image (P1) | T013-T023 | ✅ Complete |
| Phase 4: US2 — Handle Image Generation Failures (P1) | T024-T040 | ✅ Complete |
| Phase 5: US3 — Maintain Company Brand Consistency (P2) | T041-T048 | ✅ Complete |
| Phase 6: Polish & Cross-Cutting Concerns | T049-T057 | ✅ Complete |
| **Total** | **57** | **100%** |