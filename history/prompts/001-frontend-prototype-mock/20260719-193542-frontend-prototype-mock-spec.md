---
id: PHR-20260719-002
title: frontend-prototype-mock spec
stage: spec
date: 2026-07-19T19:35:42+08:00
surface: CLI
model: deepseek-v4-flash-free
feature: frontend-prototype-mock
branch: 001-frontend-prototype-mock
user: hayya
command: /sp.specify
labels: [spec, frontend, prototype, mock, ui]
links:
  spec: specs/001-frontend-prototype-mock/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - specs/001-frontend-prototype-mock/spec.md
  - specs/001-frontend-prototype-mock/checklists/requirements.md
tests:
  - N/A (specification phase)
---

## Prompt

```
## Frontend Prototype (Mocked Data)

**Intent**: Build a complete, responsive frontend prototype that allows users to interact with the marketing platform exactly as they will in production, using mocked data instead of backend APIs.

## Success Criteria

- Responsive layout works across desktop, tablet, and mobile devices
- Glassmorphism design is applied consistently throughout the application
- Single AI prompt interface serves as the primary interaction point
- Users can create, review, revise, and approve campaigns using mocked workflows
- Canvas displays AI execution animations and generated mock outputs
- Sidebar navigation provides access to company profiles, campaign history, statistics, and settings
- Entire application functions without any backend dependency
- All backend interactions are abstracted behind mock service interfaces that can later be replaced with real API calls

## Constraints

- No direct backend or database connections
- No hardcoded business logic inside UI components
- All data must come from reusable mock services
- Components must be reusable and modular
- Mobile-first responsive design
- UI should be ready for API integration without structural redesign
- Use React with the existing project stack
- Maintain consistent design system across all screens

## Non-Goals

- Backend API integration (Module 16)
- Authentication implementation
- Real AI generation
- Database persistence
- Production optimization
- Performance tuning
- Analytics
- Error monitoring
- PWA support
- Accessibility optimization
```

## Response snapshot

Created feature branch `001-frontend-prototype-mock` and wrote the specification at `specs/001-frontend-prototype-mock/spec.md`. The spec defines 5 user stories (2 P1, 2 P2, 1 P3), 14 functional requirements, 8 measurable success criteria, and 4 key entities (Campaign, Company Profile, Execution Animation Stage, Statistics). All 15 checklist items pass on first validation.

## Outcome

- ✅ Impact: Feature specification completed and validated. Ready for `/sp.plan`.
- 🧪 Tests: N/A (specification phase)
- 📁 Files: 2 files created (spec.md, checklists/requirements.md)
- 🔁 Next prompts: /sp.plan
- 🧠 Reflection: Feature description was comprehensive with clear constraints and non-goals. Zero [NEEDS CLARIFICATION] markers needed. All assumptions about mock service architecture, glassmorphism design, and responsive patterns documented.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): All 15 checklist items PASS on initial validation
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
