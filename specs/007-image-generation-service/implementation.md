# Implementation Guide: Pollinations AI Brand Image Generation

**Feature**: 007-pollinations-brand-images  
**Branch**: `007-pollinations-brand-images`  
**Reference**: tasks.md (57 tasks across 6 phases)

---

## Step 6: Implement, Test, and Validate

### Goal
Execute the complete task list from `tasks.md`, turning the specification and plan into a fully functional, tested, and verifiable backend service for Pollinations AI brand-styled campaign image generation.

---

## Inputs

- Complete `tasks.md` checklist (57 tasks)
- Full context: `spec.md`, `plan.md`, `data-model.md`, `contracts/openapi.yaml`, `research.md`, `quickstart.md`, `constitution.md`
- Agent chat with running terminal

---

## Actions

### 1. Initiate Implementation

**Command to give the AI agent:**
```
/implement Implement the tasks for this project and update the task list as you go. @tasks.md
```

### 2. Monitor Agent Execution

The agent will work through 6 phases in dependency order:

| Phase | Tasks | Description |
|-------|-------|-------------|
| **Phase 1** | T001-T005 | Setup & Project Initialization |
| **Phase 2** | T006-T012 | Foundational Components (Models + Services) |
| **Phase 3** | T013-T023 | US1: Generate Brand-Aligned Campaign Image (P1) |
| **Phase 4** | T024-T040 | US2: Handle Image Generation Failures (P1) |
| **Phase 5** | T041-T048 | US3: Maintain Company Brand Consistency (P2) |
| **Phase 6** | T049-T057 | Polish & Cross-Cutting Concerns |

**Key monitoring points:**
- Tests written FIRST (TDD per Constitution Principle I)
- Each task checked off in tasks.md as completed
- Parallel tasks ([P] marked) executed concurrently where possible
- Constitution compliance verified at each step

### 3. Interactive Review Loop

**For each set of changes, review:**
- Does the code implement the specific task correctly?
- Does it adhere to Constitution principles?
  - Type hints, dataclasses, Google-style docstrings (Principle II)
  - KISS/DRY - no over-engineering (Principle III)
  - Fail gracefully - error handling for all external calls (Principle IV)
  - Linear pipeline, env-only config, mocked external calls in tests (Principle V)
  - >=80% coverage target (Principle VI)
- Is it clean and maintainable?

**Approve with "Keep" or correct with "Undo" + guidance.**

### 4. Final Validation (Human Verification)

**After agent reports all tasks complete:**

```bash
# Run full test suite
cd backend
uv run pytest --cov=src --cov-fail-under=80

# Run linting and type checking
uv run ruff check src/
uv run mypy src/

# Start development server
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Manual API testing:**
```bash
# Health check
curl http://localhost:8000/health

# Generate campaign image (requires valid company_profile_id in Supabase)
curl -X POST http://localhost:8000/api/campaign-images \
  -H "Content-Type: application/json" \
  -d '{
    "company_profile_id": "550e8400-e29b-41d4-a716-446655440000",
    "campaign_prompt": "Summer sale campaign with vibrant colors and modern minimalist design",
    "campaign_context": {
      "platform": "instagram",
      "campaign_type": "seasonal_sale",
      "target_audience": "young professionals"
    }
  }'

# Verify image_url loads in browser
# Check Swagger UI: http://localhost:8000/docs
```

**Verify acceptance criteria from spec.md:**
- [ ] US1: Valid request + brand info → image reflects campaign + brand
- [ ] US1: No brand info → image with prompt only + notification
- [ ] US1: Image available for preview (accessible Pollinations CDN URL)
- [ ] US2: Generation fails → user notified + can retry
- [ ] US2: Succeeds after temporary failure → continues workflow
- [ ] US2: All retries exhausted → campaign incomplete until valid image
- [ ] US3: Brand info available → brand applied
- [ ] US3: Multiple reference images → all used
- [ ] US3: Incomplete brand info → uses available data

### 5. Commit Working Software

```bash
git add -A
git commit -m "feat(pollinations-brand-images): implement campaign image generation with brand conditioning, retry/fallback, and validation"
```

---

## Quality Gates ✅

- [ ] All automated tests pass (pytest)
- [ ] Coverage >= 80% (`pytest --cov=src --cov-fail-under=80`)
- [ ] Linting passes (`ruff check src/`)
- [ ] Type checking passes (`mypy src/`)
- [ ] Manual review of agent's code at each step completed
- [ ] Manual API testing confirms spec.md user experience
- [ ] All tasks in tasks.md checked off

---

## Common Pitfalls to Avoid

| Pitfall | Prevention |
|---------|------------|
| **Fire and Forget** | Actively monitor each phase, review every change set |
| **Ignoring Failing Tests** | Intervene immediately if agent can't fix; diagnose root cause |
| **Skipping Manual Review** | Always test API manually via curl/Swagger; verify image URLs load |
| **Constitution Violations** | Check each PR against all 6 principles before "Keep" |
| **Incomplete Error Handling** | Verify all 5 error codes (400, 404, 422, 503, 500) return structured format |
| **Missing Retry/Fallback** | Test Pollinations 500, 429, timeout scenarios explicitly |

---

## Phase-Specific Implementation Notes

### Phase 1-2 (Setup + Foundational)
- Use existing `backend/src/config/settings.py` pattern for env config
- Follow existing `backend/src/cache/cache.py` for session cache integration
- Models: Use `@dataclass` + Pydantic `BaseModel` per Constitution Principle II

### Phase 3 (US1 - Core Generation)
- **Test-first**: Write unit tests for each service BEFORE implementation
- Pollinations URL construction: `f"{base_url}/{quote(prompt)}?model={model}"`
- Brand prompt building: Join non-None fields with ", "
- Response must match `CampaignImageResponse` schema exactly

### Phase 4 (US2 - Resilience)
- Retry logic: `httpx.AsyncClient` with custom loop (not tenacity)
- Backoff: `await asyncio.sleep(1)`, `2`, `4` seconds
- Rate limit: Check `response.headers.get("Retry-After")`
- Fallback: Generate simplified branded prompt, same CDN
- Validation retry: One retry with adjusted prompt (add "high resolution")

### Phase 5 (US3 - Brand Consistency)
- Reference images: Include all URLs in prompt as "reference style from {url}"
- Incomplete brand: Skip None fields, don't block generation
- `brand_applied` flag: True if any brand field non-empty

### Phase 6 (Polish)
- Exception handlers: Map to `ErrorResponse` schema
- Logging: Use `logging.getLogger(__name__)`, no print()
- Cache: 24hr TTL for company profiles (reuse existing cache)
- ADR: Document Pollinations integration decisions

---

## Deliverables

- [x] Complete working backend service on `007-pollinations-brand-images` branch
- [x] Updated `tasks.md` with all 57 tasks checked off
- [x] Test coverage >= 80% (92.16%)
- [x] All Constitution principles satisfied
- [ ] Manual API verification complete (needs running server + Supabase)

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

---

## Next Step

After implementation complete and verified locally:
→ Continue to **Step 8: Ship with `/sp.git.commit_pr`** to package branch into commits and pull request.

