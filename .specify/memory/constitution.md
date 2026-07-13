<!--
  Sync Impact Report
  ==================
  Version change: (new) 0.0.0 → 1.0.0
  Modified principles: N/A (first fill from template)
  Added sections:
    - 6 Core Principles (Test-First, Clean Code & Type Safety, KISS & DRY, Fail Gracefully, Architecture Constraints, Code Quality & Coverage)
    - Technical Stack & Architecture
    - Testing, Documentation & Quality Gates
    - Governance
  Removed sections: N/A
  Templates requiring updates:
    - .specify/templates/plan-template.md: ⚠ pending (Constitution Check section references generic gates - should align with new principles)
    - .specify/templates/spec-template.md: ⚠ pending (no constitution-specific references found)
    - .specify/templates/tasks-template.md: ⚠ pending (no constitution-specific references found)
  Follow-up TODOs:
    - RATIFICATION_DATE: unknown - set when constitution is formally adopted by stakeholders
-->

# AI Social Campaign Manager Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)

All features MUST have corresponding tests written before implementation.
Tests MUST be written, reviewed, and confirmed failing before any production
code is written. This applies to unit, integration, and end-to-end tests.
Rationale: Ensures every feature is verifiable from the start and prevents
untested code from entering the codebase.

### II. Clean Code & Type Safety

Python 3.10+ with comprehensive type hints for all functions and methods.
Prioritize readability, maintainability, and self-documenting code. Use
dataclasses for all data structures. All public functions MUST have Google-style
docstrings. Complex logic MUST include inline comments explaining "why" not
"what". No print statements — use logger instead.

### III. KISS & DRY

Keep It Simple, Stupid. Avoid over-engineering; use simple dict-based session
cache over Redis for V1. Don't Repeat Yourself — reuse company profile logic
across all campaign types. Start simple, YAGNI principles. No RAG/Vector
Embeddings — simple key-value lookup by company_id is sufficient.

### IV. Fail Gracefully

Always provide user-friendly error messages and manual fallbacks when
third-party services fail. Implement proper error handling for all external API
calls. Log all third-party service failures with appropriate context. Never
expose raw error details to end users.

### V. Architecture Constraints

Linear Pipeline — LangGraph NOT required for V1; use custom Python orchestration
logic. Ephemeral Guest Data — never persist guest information to database;
session cache only (24-hour expiry). Environment Variables Only — no hardcoded
API keys (LLM, Pollinations, Supabase). All external API calls MUST be mocked in
tests.

### VI. Code Quality & Coverage

All tests must pass before merging. Minimum 80% code coverage. Implement proper
error handling for all external API calls. Log all third-party service failures
with appropriate context. No print statements — use logger instead. Type hints
for all function parameters and return values.

## Technical Stack & Architecture

### Backend
- **Language:** Python 3.10+ (project requires >=3.13)
- **Framework:** FastAPI (async support)
- **Package Manager:** pip / poetry
- **Testing:** pytest with coverage plugin
- **Orchestration:** Custom Python logic (no LangGraph for V1)

### Database & Storage
- **Database:** Supabase (PostgreSQL) — company_profiles table only
- **Storage:** Supabase Storage (public bucket) — brand reference images
- **Session Cache:** Python dict with 24-hour TTL (per session)

### AI & APIs
- **LLM:** OpenAI GPT-4o or Google Gemini (via official SDK)
- **Image Generation:** Pollinations AI (kontext model) with image parameter
- **Web Search:** duckduckgo-search (ddgs) with 5-second rate limit + 15-second timeout
- **Image Validation:** Pillow (PIL) for resolution checks (>=1080x1080)

### Frontend
- **Framework:** Next.js 14+ (App Router) + React 18+
- **Language:** TypeScript 5+
- **UI:** Tailwind CSS 3+ + shadcn/ui components
- **State:** React Context API + Zustand (chat state)
- **API Client:** TanStack Query (React Query)

### Deployment
- **Containerization:** Docker
- **Hosting:** VPS (DigitalOcean, AWS EC2, or Google Cloud Run)
- **CI/CD:** GitHub Actions or similar

### Project Structure

```
ai-social-campaign-manager/
├── backend/
│   ├── src/
│   │   ├── api/              # FastAPI route handlers
│   │   ├── agents/           # 6 campaign type agents
│   │   ├── orchestrator.py   # Main pipeline orchestration
│   │   ├── services/         # DDGS, LLM, Pollinations, Supabase, validation
│   │   ├── models/           # Dataclasses + Pydantic schemas
│   │   ├── cache/            # In-memory session cache
│   │   ├── config/           # Environment variables + config
│   │   └── main.py           # FastAPI entry point
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── conftest.py
│   │   └── __init__.py
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .python-version
│   └── Dockerfile
├── frontend/
│   ├── app/                  # Next.js App Router
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md

## Testing, Documentation & Quality Gates

### Testing Standards

**Test Categories:**
- **Unit Tests** — Test individual components in isolation
- **Integration Tests** — Test service interactions (DDGS, LLM, Pollinations with mocks)
- **API Tests** — Test FastAPI endpoints with TestClient
- **End-to-End Tests** — Test complete workflow (with mocked external services)

**Test Requirements:**
- All external API calls MUST be mocked in tests
- Test both success and failure scenarios for all third-party services
- Test DDGS rate limiter and timeout behavior
- Test image resolution validation (>=1080x1080)
- Test character limit validation (LinkedIn <=3000, Instagram <=2200)
- Test session cache expiry (24-hour TTL)
- Test all 6 campaign agents with different system prompts

**Coverage Requirements:**
- Minimum 80% code coverage for backend
- Focus coverage on critical paths: orchestration, validation, and service wrappers
- Generate coverage reports with `pytest --cov`

### Documentation Standards

**Required Documentation:**
- API Documentation — Auto-generated with FastAPI (OpenAPI/Swagger)
- README.md — Setup, installation, and quick start guide
- ADR (Architecture Decision Records) — For all significant architectural decisions
- System Prompts — Document all 6 campaign type prompts in /docs/prompts/

**Code Documentation:**
- All public functions MUST have Google-style docstrings
- Complex logic MUST have inline comments explaining "why" not "what"
- Type hints for all function parameters and return values

### Code Review Requirements

**Before Submission:**
- [ ] All tests pass locally
- [ ] Coverage >=80%
- [ ] No hardcoded API keys or sensitive data
- [ ] Error handling for all external API calls
- [ ] Type hints added for all new functions
- [ ] Documentation updated for new features
- [ ] No print statements (use logger instead)

**Review Focus Areas:**
- Error handling and graceful degradation
- Security (API keys, data exposure)
- Performance (API call optimization, caching)
- Code maintainability and readability
- Compliance with project principles

### Deployment Standards

**Pre-Deployment Checklist:**
- [ ] All environment variables configured
- [ ] Supabase tables and storage buckets created
- [ ] API rate limits configured (DDGS: 5s, Pollinations: as needed)
- [ ] Error monitoring configured (e.g., Sentry)
- [ ] Logging configured for production
- [ ] Health check endpoint tested

**Rollback Plan:**
- Docker image tagging with version numbers
- Ability to rollback to previous stable version
- Database migrations must be reversible

### Performance Requirements

- End-to-end generation (text + image): <=60 seconds
- DDGS search timeout: 15 seconds
- Rate limiter: 5-second minimum between DDGS calls
- Session cache: 24-hour TTL

### Quality Gates

**Must Pass Before Release:**
1. **Code Quality** — Flake8/Pylint with no errors
2. **Tests** — All tests passing with >=80% coverage
3. **Manual QA** — 90% of users rate preview as "professional"
4. **Validation** — 100% of images pass >=1080x1080 resolution
5. **Character Limits** — 100% of posts pass platform limits
6. **Branding** — 95% of posts use brand tone + reference image style
7. **Approval Required** — 0 posts published without explicit "Approve"

### Success Criteria

1. Generate professional-looking campaign previews (>=90% user rating)
2. Each generated post includes at least 1 CTA
3. 100% images pass resolution check (>=1080x1080)
4. 100% generated posts pass character limit check
5. 95% posts maintain brand tone + reference image style
6. Zero posts published without explicit "Approve" click

## Governance

This constitution is the authoritative source for project principles, standards,
and quality requirements. All contributions MUST comply with these standards.

**Amendment Procedure:**
1. Proposed changes MUST be documented with rationale
2. Changes MUST be reviewed and approved by project stakeholders
3. Version MUST be bumped according to semantic versioning rules:
   - MAJOR: Backward incompatible principle removals or redefinitions
   - MINOR: New principle/section added or materially expanded guidance
   - PATCH: Clarifications, wording, typo fixes, non-semantic refinements
4. All PRs and reviews MUST verify compliance with this constitution
5. Complexity MUST be justified when it violates KISS/DRY principles

**Compliance Review:**
- Every feature plan MUST include a Constitution Check section
- Code review MUST verify compliance with all applicable principles
- Quality gates MUST be verified before any release

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): unknown - set when formally adopted by stakeholders | **Last Amended**: 2026-07-13
