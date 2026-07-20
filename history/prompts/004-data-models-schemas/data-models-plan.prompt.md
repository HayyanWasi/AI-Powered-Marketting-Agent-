---
id: phr-004-002
title: data-models-plan
stage: plan
date: 2026-07-14
surface: opencode-cli
model: deepseek-v4-flash-free
feature: data-models-schemas
branch: 004-data-models-schemas
user: hayya
command: /sp.plan
labels: [plan, data-models, core-services]
links:
  spec: specs/004-data-models-schemas/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - specs/004-data-models-schemas/plan.md
  - specs/004-data-models-schemas/research.md
  - specs/004-data-models-schemas/data-model.md
  - specs/004-data-models-schemas/quickstart.md
  - specs/004-data-models-schemas/contracts/pydantic-schemas.md
tests:
  - specs/004-data-models-schemas/checklists/requirements.md
---

## Prompt

User requested plan creation for data models & schemas: /sp.plan

## Response snapshot

Created implementation plan with Technical Context, Constitution Check (PASS), and Project Structure. Phase 0 research resolved 5 design decisions (dual representation pattern, campaign type/status validation, URL validation, company compatibility). Phase 1 produced data-model.md with Guest/Campaign/Company entities, contracts/pydantic-schemas.md with all Create/Update/Response schemas, and quickstart.md with usage examples. Updated AGENTS.md via update-agent-context.ps1.

## Outcome

- ✅ Impact: Plan complete and ready for tasking phase
- 🧪 Tests: 100% coverage target for model validation paths
- 📁 Files: plan.md, research.md, data-model.md, quickstart.md, contracts/pydantic-schemas.md
- 🔁 Next prompts: /sp.tasks
- 🧠 Reflection: No NEEDS CLARIFICATION needed — existing company.py pattern provides clear template

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
