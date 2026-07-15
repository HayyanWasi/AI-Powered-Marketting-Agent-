---
id: phr-004-003
title: data-models-tasks
stage: tasks
date: 2026-07-14
surface: opencode-cli
model: deepseek-v4-flash-free
feature: data-models-schemas
branch: 004-data-models-schemas
user: hayya
command: /sp.tasks
labels: [tasks, data-models, core-services]
links:
  spec: specs/004-data-models-schemas/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - specs/004-data-models-schemas/tasks.md
tests:
  - specs/004-data-models-schemas/checklists/requirements.md
---

## Prompt

User requested task generation for data models & schemas: /sp.tasks

## Response snapshot

Generated tasks.md with 34 tasks across 5 phases: Setup (T001, __init__.py exports), US1 Guest model (T002-T011, 6 tests + 4 impl), US2 Campaign model (T012-T022, 7 tests + 4 impl), US3 Company verification (T023-T030, 7 tests + 1 impl verification), Polish (T031-T034, ruff/mypy/pytest/coverage). All three P1 stories can run in parallel since they target different files. All tasks follow strict checklist format with [P] parallel markers and [US1]/[US2]/[US3] story labels.

## Outcome

- ✅ Impact: Task list complete and immediately executable
- 🧪 Tests: 20 test tasks covering all FR-05 and FR-10 requirements
- 📁 Files: tasks.md
- 🔁 Next prompts: TDD red/green implementation (manual execution)
- 🧠 Reflection: All three stories are P1 and independent — parallel execution is optimal

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
