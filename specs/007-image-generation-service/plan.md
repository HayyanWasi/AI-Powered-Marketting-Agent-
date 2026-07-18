# Implementation Plan: Pollinations AI Brand Image Generation

**Branch**: `007-pollinations-brand-images` | **Date**: 2026-07-15 | **Spec**: [spec.md](spec.md)

## Summary

Integrate Pollinations AI (kontext model) to generate campaign images with brand style conditioning from company profiles. The system accepts campaign prompts and company profile IDs, constructs brand-conditioned prompts, calls the Pollinations API with retry/fallback logic, validates generated images (>=1080x1080), and returns accessible image URLs for frontend preview.

## Technical Context

**Language/Version**: Python 3.13 (project requires >=3.13)  
**Primary Dependencies**: FastAPI, httpx (async HTTP), Pydantic v2, Pillow (PIL) for image validation, Supabase Python SDK  
**Storage**: Supabase PostgreSQL (company_profiles table), Supabase Storage (brand reference images - public bucket)  
**Testing**: pytest with pytest-asyncio, pytest-cov (>=80% coverage), httpx.AsyncClient for API tests  
**Target Platform**: Linux server (Docker container)  
**Project Type**: Web application backend (FastAPI)  
**Performance Goals**: 
- API response overhead <500ms p95 (excluding Pollinations generation)
- 30s total timeout including retries
- 95% success rate for image generation
**Constraints**: 
- No API key for Pollinations (public API)
- Brand assets read-only from Supabase
- Direct CDN URLs from Pollinations (no local storage)
- Environment variables only for config (no hardcoded secrets)
**Scale/Scope**: Single image generation per request, ~10k users, moderate concurrent load

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Test-First**: Tests written before implementation (Principle I)
- [x] **Clean Code**: Type hints, dataclasses, Google-style docstrings, no print statements (Principle II)
- [x] **KISS/DRY**: Simple dict-based session cache, reuse company profile logic, no RAG (Principle III)
- [x] **Fail Gracefully**: Retry logic, fallback images, user-friendly errors, logged failures (Principle IV)
- [x] **Architecture**: Linear pipeline, custom Python orchestration, env-only config, mocked external calls in tests (Principle V)
- [x] **Coverage**: >=80% code coverage target (Principle VI)
- [x] **Stack**: Uses approved stack (FastAPI, Supabase, Pollinations, Pillow, httpx)

**Post-Design Re-evaluation**: All principles remain satisfied. No new violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/007-pollinations-brand-images/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── openapi.yaml     # API contract
└── tasks.md             # Phase 2 output (created by /sp.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── routes/
│   │       └── campaign_images.py      # POST /api/campaign-images
│   ├── services/
│   │   ├── pollinations_service.py     # Pollinations API client with retry/fallback
│   │   ├── brand_style_service.py      # Brand context extraction & prompt building
│   │   ├── image_validation_service.py # Image resolution/format validation
│   │   └── company_profile_service.py  # Supabase company profile access
│   ├── models/
│   │   ├── campaign_image.py           # Request/Response dataclasses
│   │   └── brand_style.py              # BrandStyleContext dataclass
│   ├── cache/
│   │   └── cache.py                    # Session cache (existing)
│   ├── config/
│   │   └── settings.py                 # Environment config (existing)
│   └── main.py                         # FastAPI entry point (existing)
├── tests/
│   ├── unit/
│   │   ├── test_brand_style_service.py
│   │   ├── test_pollinations_service.py
│   │   └── test_image_validation_service.py
│   ├── integration/
│   │   └── test_campaign_image_api.py
│   └── conftest.py
├── pyproject.toml
├── uv.lock
└── Dockerfile
```

**Structure Decision**: Option 2 (Web application backend) — matches existing backend/ structure with FastAPI routes, services, models, and tests directories.

## Architecture

**API Endpoint**: POST `/api/campaign-images`
- Request: `{ "company_profile_id": "uuid", "campaign_prompt": "string", "campaign_context": "object" }`
- Response: `{ "image_url": "https://image.pollinations.ai/...", "model": "kontext", "generation_time_ms": 1234, "fallback_used": false }`

**Validation Layer**: Pydantic models for request/response validation, Pillow for image validation (>=1080x1080)

**Pollinations Client**: httpx.AsyncClient with:
- Base URL: `https://image.pollinations.ai/prompt/`
- Model parameter: `model=kontext`
- Timeout: 30 seconds
- Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
- Rate limit handling: Respect `Retry-After` header on 429

**Brand Style Conditioning**: 
- Extract brand_colors, brand_personality, style_guide, logo_url from company profile
- Build prompt: `"{campaign_prompt}, brand colors {colors}, {personality} style, {style_guide}"`
- Include reference image URLs if available

**Image Validation**: 
- Fetch image via HEAD request to verify URL accessibility
- Download and validate resolution >= 1080x1080 using Pillow
- Validate content-type is image/*

**Error Handling & Fallback**:
- On API failure after retries: Generate branded fallback via Pollinations with simplified prompt
- On validation failure: Retry generation once with adjusted prompt
- On total failure: Return structured error with retry guidance

**Database**: Supabase `company_profiles` table (existing from feature 002)

## Dependency Sequence

1. **Data Models** (models/campaign_image.py, models/brand_style.py)
   - Request/Response dataclasses, BrandStyleContext
   - Acceptance: Type checks pass, serialization works

2. **Company Profile Service** (services/company_profile_service.py)
   - Fetch company profile by ID from Supabase
   - Acceptance: Returns profile with brand fields, handles not found

3. **Brand Style Service** (services/brand_style_service.py)
   - Extract BrandStyleContext from company profile
   - Build Pollinations prompt with brand conditioning
   - Acceptance: Unit tests cover all brand field combinations

4. **Pollinations Service** (services/pollinations_service.py)
   - Async HTTP client with retry/fallback logic
   - Generate image URL with kontext model
   - Acceptance: Integration tests with mocked Pollinations API

5. **Image Validation Service** (services/image_validation_service.py)
   - Validate image URL accessibility and resolution
   - Acceptance: Tests pass for valid/invalid images

6. **API Endpoint** (api/routes/campaign_images.py)
   - POST /api/campaign-images handler
   - Orchestrates services, returns response
   - Acceptance: Integration tests pass (success, validation error, not found, API failure)

7. **Error Handling Middleware** (if not existing)
   - Structured error responses for all failure modes
   - Acceptance: All error paths return consistent format

## Testing Strategy

**Unit Tests** (backend/tests/unit/):
- `test_brand_style_service.py`: Prompt building with various brand field combinations (empty, partial, complete)
- `test_pollinations_service.py`: Retry logic, fallback generation, timeout handling, rate limit handling (mocked httpx)
- `test_image_validation_service.py`: Resolution validation, URL accessibility, content-type checks

**Integration Tests** (backend/tests/integration/):
- `test_campaign_image_api.py`: Full API flow with mocked Supabase and Pollinations
  - Success: Valid request → brand prompt → Pollinations → validation → 200 response
  - Missing company: 404 with structured error
  - Validation failure: 422 with details
  - Pollinations failure: 503 with fallback info
  - Retry success: Transient 500 → retry → success

**Edge Case Tests**:
- Empty campaign prompt → 400 validation error
- Company profile with no brand fields → prompt without brand conditioning + user notification
- Multiple reference images → all included in prompt
- Rate limit (429) → respects Retry-After header
- Invalid image URL → validation fails → retry once → fallback
- Generated image < 1080x1080 → validation fails → retry with adjusted prompt

**Load Tests** (manual/separate):
- 100 concurrent requests → verify p95 < 500ms API overhead
- Sustained rate → verify retry/fallback behavior under load

## Tradeoffs

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Direct Pollinations CDN URLs (no local storage) | Simplicity, cost, CDN performance | Download to Supabase Storage: adds latency, storage cost, complexity |
| Prompt engineering for brand conditioning | No fine-tuning needed, works with kontext model | Custom model training: cost, time, maintenance; ControlNet: not available on Pollinations |
| httpx.AsyncClient with custom retry | Full control over backoff, timeout, fallback | tenacity library: adds dependency; built-in httpx retry: limited fallback support |
| Pillow for image validation | Standard, lightweight, no external service | External validation API: latency, cost, dependency |
| Exponential backoff (1s, 2s, 4s) | Respects server, handles transient errors | Fixed interval: less adaptive; Fibonacci: over-engineered |
| Single kontext model | Spec requirement, best quality on Pollinations | Multiple models: adds complexity, not requested |
| Fallback via Pollinations (not static) | Consistent branding, always available | Static placeholder: no brand colors, manual maintenance |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Custom retry/fallback logic in Pollinations service | Principle IV (Fail Gracefully) requires proper handling of all external call failures; tenacity would be extra dependency | Direct httpx retry: limited fallback support; tenacity: adds dependency for simple logic |

## Phase 1: Design & Contracts (Next Steps)

1. **Generate data-model.md** from entities in spec
2. **Generate contracts/openapi.yaml** from FR-01, FR-04, FR-06
3. **Generate quickstart.md** for local testing
4. **Run agent context update** to add Pollinations, Pillow to agent config

---

*Plan generated from spec.md and research.md. Ready for Phase 1 execution.*