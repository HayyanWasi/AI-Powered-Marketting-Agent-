---
id: phr-004-001
title: data-models-specification
stage: spec
date: 2026-07-14
surface: opencode-cli
model: deepseek-v4-flash-free
feature: data-models-schemas
branch: 004-data-models-schemas
user: hayya
command: /sp.specify
labels: [spec, data-models, core-services]
links:
  spec: specs/004-data-models-schemas/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - specs/004-data-models-schemas/spec.md
tests:
  - specs/004-data-models-schemas/checklists/requirements.md
---

## Prompt

User provided feature description for "Data Models & Schemas" — define all data structures as Python dataclasses and Pydantic schemas with validation. FR-05, FR-10. Entities: Guest, Campaign, Company.

## Response snapshot

Created branch `004-data-models-schemas`, wrote full specification with 3 user stories (Guest model, Campaign model, Company model), 12 functional requirements (FR-05-01 through FR-05-11 + FR-10-01, FR-10-02), 3 key entities, 5 success criteria, 8 edge cases. Quality checklist generated and all items pass. No NEEDS CLARIFICATION markers needed.

## Outcome

- ✅ Impact: Spec complete and ready for planning phase
- 🧪 Tests: 100% coverage target for model validation paths
- 📁 Files: spec.md, checklists/requirements.md
- 🔁 Next prompts: /sp.plan
- 🧠 Reflection: No NEEDS CLARIFICATION needed — fields and constraints have reasonable defaults

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
