# Implementation Plan: Campaign Management Module

**Branch**: `010-campaign-management` | **Date**: 2026-07-16 | **Spec**: specs/010-campaign-management/spec.md
**Input**: Feature specification from `/specs/010-campaign-management/spec.md`

## Summary

Build a Campaign Management module that serves as the single source of truth for all campaign business data. The module manages the complete campaign lifecycle (Draft → Ready → Review → Approved → Published → Archived), enforces valid state transitions, maintains an immutable append-only history of all changes, stores campaign assets (copy, images, hashtags, metadata), and provides a public API for downstream modules (Campaign Generation, Publishing, future Analytics). The implementation uses Python 3.13+ with FastAPI, Supabase PostgreSQL for persistence, and a deterministic code-level state machine to validate transitions before database writes.

## Technical Context

**Language/Version**: Python 3.13+ (FastAPI)
**Primary Dependencies**: FastAPI, Supabase Python SDK, Pydantic v2, asyncpg (via Supabase), pytest, httpx
**Storage**: Supabase PostgreSQL (campaigns, campaign_configurations, campaign_history, campaign_assets tables) + Supabase Storage (for asset binaries if needed)
**Testing**: pytest with pytest-asyncio, pytest-cov, TestClient for FastAPI
**Target Platform**: Linux server (Docker container)
**Project Type**: Backend service (FastAPI API)
**Performance Goals**: 
- Campaign CRUD operations < 100ms p95
- History queries < 1s for 500 entries
- Campaign listing with filters < 500ms for 10k campaigns
**Constraints**: 
- Must remain completely independent of AI generation, prompts, models, workflow orchestration
- Campaign updates must be atomic (transactional)
- History must be append-only and immutable
- Business validation before any persistent state change
- Optimistic concurrency control for updates
- No LangGraph (constitution Principle V: Linear Pipeline)
**Scale/Scope**: 
- Support 10k+ campaigns per tenant
- Up to 500 history entries per campaign
- Multi-tenant via organization_id

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Test-First**: Tests written before implementation? (Principle I) — Will generate test specifications in Phase 1
- [x] **Clean Code**: Type hints, dataclasses, docstrings, no print statements? (Principle II) — Plan uses dataclasses and Pydantic models
- [x] **KISS/DRY**: No over-engineering, no unnecessary abstractions? (Principle III) — Simple state machine, no LangGraph, reuses Company Profile patterns
- [x] **Fail Gracefully**: Error handling for all external calls? (Principle IV) — Plan includes error handling for Supabase calls
- [x] **Architecture**: Linear pipeline, no RAG, env-only config? (Principle V) — Uses custom Python state machine, no LangGraph
- [x] **Coverage**: >=80% code coverage target? (Principle VI) — Will specify in test strategy
- [x] **Stack**: Uses approved tech stack (FastAPI, Supabase, Next.js, etc.)? — FastAPI, Supabase (PostgreSQL + Storage), Pydantic

## Project Structure

### Documentation (this feature)

```text
specs/010-campaign-management/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── openapi.yaml
└── tasks.md             # Phase 2 output (/sp.tasks command)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── routes/
│   │       └── campaigns.py        # Campaign CRUD + state transitions + history
│   ├── models/
│   │   ├── campaign.py             # Campaign, CampaignState, CampaignAsset dataclasses
│   │   └── history.py              # CampaignHistoryEntry dataclass
│   ├── services/
│   │   ├── campaign_service.py     # Business logic: CRUD, transitions, validation
│   │   ├── state_machine.py        # Deterministic state machine
│   │   ├── history_service.py      # Append-only history logging
│   │   └── asset_service.py        # Asset association
│   ├── repositories/
│   │   ├── campaign_repository.py  # Data access for campaigns
│   │   ├── history_repository.py   # Data access for history
│   │   └── asset_repository.py     # Data access for assets
│   ├── config/
│   │   └── settings.py             # Supabase config, feature flags
│   └── main.py                     # FastAPI entry point (adds campaign routes)
└── tests/
    ├── unit/
    │   ├── test_state_machine.py
    │   ├── test_campaign_model.py
    │   └── test_history_service.py
    ├── integration/
    │   ├── test_campaign_api.py
    │   └── test_history_immutability.py
    └── conftest.py
```

**Structure Decision**: Backend-only feature following the existing repository structure (backend/src with api, models, services, repositories). Frontend integration will be handled separately.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Repository pattern | Separates data access from business logic; enables testing with mocks | Direct DB calls in services would make unit testing difficult and couple logic to Supabase SDK |

---

## Phase 0: Research

*All NEEDS CLARIFICATION items from Technical Context resolved here.*

### Research Tasks

1. **Supabase Python SDK async patterns** — Best practices for async database operations with Supabase in FastAPI context
2. **Optimistic locking implementation** — Version-based concurrency control with Supabase/PostgreSQL
3. **Append-only history table design** — PostgreSQL patterns for immutable audit logs (triggers, RLS, or application-level)
4. **State machine libraries vs custom** — Evaluate `transitions` library vs custom implementation for determinism
5. **Campaign asset storage** — Supabase Storage integration for binary assets vs database-only references

---

## Phase 1: Design & Contracts

### 1. Data Model (`data-model.md`)

**Entities from spec:**
- **Campaign**: id, name, goals, target_audience, platforms, schedule, metadata, state, version, timestamps, organization_id, company_profile_id
- **CampaignHistoryEntry**: id, campaign_id, event_type, timestamp, actor_id, from_state, to_state, changed_fields (JSON), snapshot (JSON)
- **CampaignAsset**: id, campaign_id, asset_type, content (JSON/text), source, created_at
- **CampaignState**: Enum (Draft, Ready, Review, Approved, Published, Archived)

**Validation Rules:**
- Name required, unique per organization
- Goals, target_audience, platforms, schedule required
- State transitions per FR-008
- Version increments on each update (optimistic locking)
- History entries immutable (no UPDATE/DELETE)

### 2. API Contracts (`contracts/openapi.yaml`)

**Endpoints:**
- `POST /api/v1/campaigns` — Create campaign (Draft)
- `GET /api/v1/campaigns` — List with filters (state, date_range, owner, pagination)
- `GET /api/v1/campaigns/{campaign_id}` — Get campaign with config, assets, history summary
- `PUT /api/v1/campaigns/{campaign_id}` — Update configuration (Draft only, atomic, version check)
- `POST /api/v1/campaigns/{campaign_id}/transition` — State transition with validation
- `POST /api/v1/campaigns/{campaign_id}/archive` — Archive campaign
- `POST /api/v1/campaigns/{campaign_id}/restore` — Restore archived campaign
- `GET /api/v1/campaigns/{campaign_id}/history` — Paginated history
- `POST /api/v1/campaigns/{campaign_id}/assets` — Associate asset
- `GET /api/v1/campaigns/{campaign_id}/assets` — List assets

**Error Codes:**
- 400: Invalid input / missing required fields
- 404: Campaign not found
- 409: Invalid state transition / version conflict / duplicate name
- 422: Validation error

### 3. Quickstart (`quickstart.md`)

Step-by-step curl examples for:
- Create campaign
- Update draft configuration
- Transition through lifecycle (Draft → Ready → Review → Approved → Published)
- View history
- Archive and restore
- Associate assets
- List with filters

### 4. Agent Context Update

Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType opencode` to add new technology choices.

---

## Phase 2: Task Generation (for `/sp.tasks`)

*Not created by this command — will be generated by `/sp.tasks` based on this plan.*

**Dependencies:**
1. Database schema (campaigns, campaign_configurations, campaign_history, campaign_assets)
2. Data Access Layer with transaction support
3. State machine implementation
4. API routes and validation
5. History service
6. Asset service
7. Tests (unit + integration)

**Test Strategy:**
- Unit: State machine transitions (valid/invalid), input validation, history immutability
- Integration: DB transactions, history append on state change, rollback on failure, optimistic locking
- Performance: Query optimization, indexing, <100ms CRUD, <1s history for 500 entries
- Boundary: No AI logic leakage, state machine independent of workflow orchestration