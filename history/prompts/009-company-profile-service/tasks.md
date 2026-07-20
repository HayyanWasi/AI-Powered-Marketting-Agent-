---
id: phr-009-company-profile-service-tasks
title: Company Profile Tasks Generation
stage: tasks
date: 2026-07-15
surface: cli
model: deepseek-v4-flash-free
feature: Company Profile Service
branch: 009-company-profile-service
user: hayya
command: /sp.tasks
labels: [tasks, company-profile, task-breakdown]
links:
  spec: specs/009-company-profile-service/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/009-company-profile-service/tasks.md
tests:
  - null
---

## Prompt

Execute the `/sp.tasks` workflow for the 009-company-profile-service feature. Run check-prerequisites.ps1, load design documents, and write the user-provided task breakdown to tasks.md following the task generation rules and template format.

## Response snapshot

Completed task generation for Company Profile Service:

1. **Prerequisites check**: All design documents present (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)
2. **tasks.md written** with the user-provided breakdown adapted to template format:
   - 8 phases covering Setup, Foundational, 5 user stories, and Polish
   - 36 total tasks (T001–T036) with proper [P] and [US*] markers
   - Dependency graph, parallel execution table, and incremental delivery strategy
3. **Format validation**: All tasks follow `- [ ] [TaskID] [P?] [Story?] Description` format with file paths

## Outcome

- ✅ Impact: Complete task list ready for implementation
- 📁 Files: tasks.md (36 tasks across 8 phases)
- 🔁 Next prompts: Implementation via TDD (red/green/refactor cycles)
- 🧠 Reflection: Tasks organized by user story priority (P1 → P2 → P3). Phase dependencies clearly mapped. MVP scope = Phase 1 + Phase 2 + US1 + US2.
