---
id: 004-004
title: implement-data-models-schemas
stage: green
date: 2026-07-15
surface: CLI
model: deepseek-v4-flash-free
feature: 004-data-models-schemas
branch: 004-data-models-schemas
user: HayyanWasi
command: (conversation) Full implementation of data models — Guest, Campaign, Company with dataclasses + Pydantic schemas + tests
labels: [green, implementation]
links:
  spec: specs/004-data-models-schemas/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - backend/src/models/__init__.py (update exports)
  - backend/src/models/guest.py (new: Guest dataclass + GuestCreate/Update/Response Pydantic)
  - backend/src/models/campaign.py (new: Campaign dataclass + CampaignCreate/Update/Response Pydantic)
  - backend/src/models/company.py (update: added whitespace validation pattern)
  - backend/tests/unit/test_guest_model.py (new: 12 tests)
  - backend/tests/unit/test_campaign_model.py (new: 12 tests)
  - backend/tests/unit/test_company_model.py (new: 11 tests)
tests:
  - backend/tests/unit/test_guest_model.py
  - backend/tests/unit/test_campaign_model.py
  - backend/tests/unit/test_company_model.py
---

## Prompt

Implement the full data models & schemas feature (004-data-models-schemas) following the outline tasks in tasks.md: Guest dataclass + Pydantic schemas (US1), Campaign dataclass + Pydantic schemas (US2), Company model verification + standalone tests (US3). Run ruff, mypy, pytest, coverage and mark all tasks [X] upon completion.

## Response snapshot

Executed all 34 tasks across 5 phases:
- Phase 1 (Setup): Updated `__init__.py` to expose Guest and Campaign types
- Phase 2 (US1 Guest): Created `guest.py` with Guest dataclass (uuid4 id, name/title/company/bio, to_response()), GuestCreate (name required 1-255 + whitespace pattern), GuestUpdate (all optional), GuestResponse; 12 tests
- Phase 3 (US2 Campaign): Created `campaign.py` with Campaign dataclass (type/caption required, image_url default "", status default "draft"), CampaignCreate (type+caption required, image_url optional HttpUrl, status with regex `^(draft|published|archived)$`), CampaignUpdate (all optional), CampaignResponse; 12 tests
- Phase 4 (US3 Company): Verified existing `company.py`, added whitespace validation patterns to CompanyProfileCreate/Update, 11 standalone tests
- Phase 5 (Polish): Ruff ✓, mypy ✓, pytest 35/35 ✓, coverage 100% on src.models

Fixed 3 whitespace-validation tests that initially failed (Pydantic min_length accepts whitespace-only strings — added `pattern=r".*\S.*"` to GuestCreate.name, CampaignCreate.caption, CompanyProfileCreate.name/tone).

## Outcome

- ✅ Impact: Core data model layer complete — Guest, Campaign, Company with dual dataclass+Pydantic representation, full validation (required fields, string lengths, URL format, status enum, whitespace rejection), and JSON serialization round-trips.
- 🧪 Tests: 35 tests, all passing. Coverage 100% on `backend.src.models` (4 modules: __init__, guest, campaign, company).
- 📁 Files: 7 files touched (3 new source, 1 updated source, 3 new test). Ruff + mypy clean.
- 🔁 Next prompts: Wire models into API routes; add persistence layer.
- 🧠 Reflection: TDD approach worked well — tests caught whitespace-validation gap immediately. Three models could genuinely be implemented in parallel since they share no files.

## Evaluation notes (flywheel)

- Failure modes observed: Pydantic `min_length` only checks string length, not content — "   " passes min_length=1. Need explicit pattern for whitespace rejection.
- Graders run and results (PASS/FAIL): Ruff PASS, mypy PASS, pytest 35/35 PASS, coverage 100% PASS.
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add model persistence/CRUD integration tests.
