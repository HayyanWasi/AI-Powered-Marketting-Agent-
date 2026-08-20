# Tasks: Frontend Prototype (Mocked Data)

**Input**: Design documents from `specs/015-frontend-prototype-mock/`

**Prerequisites**:
- plan.md
- spec.md
- research.md
- data-model.md
- contracts/

**Organization**: Tasks are grouped by user story so every story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Project Setup

**Purpose**: Create the frontend foundation shared by every feature.

- [ ] T001 Initialize Next.js App Router project structure under `frontend/src/`
- [ ] T002 [P] Configure Tailwind CSS, shadcn/ui and global glassmorphism theme in `frontend/tailwind.config.ts`
- [ ] T003 [P] Configure routing, layouts and responsive breakpoints in `frontend/src/app/layout.tsx`
- [ ] T004 [P] Create shared TypeScript types from `data-model.md` in `frontend/src/types/`
- [ ] T005 [P] Create service interfaces in `frontend/src/services/interfaces/`
- [ ] T006 [P] Create mock service implementations in `frontend/src/services/mock/`
- [ ] T007 Configure application provider for service switching in `frontend/src/app/providers.tsx`
- [ ] T008 [P] Configure global theme, fonts and reusable UI primitives in `frontend/src/lib/theme.ts` and `frontend/src/components/ui/`

**Checkpoint**: Frontend foundation completed.

---

## Phase 2: User Story 1 — AI Campaign Workspace (P1) 🎯 MVP

**Goal**: Users can immediately begin creating campaigns through a prompt-based workspace.

**Independent Test**: Open the application, enter a prompt, submit it and verify that the workspace transitions into campaign generation.

### Implementation

- [ ] T009 [US1] Build application shell with sidebar and workspace layout in `frontend/src/components/layout/`
- [ ] T010 [P] [US1] Build prompt input component in `frontend/src/components/chat/prompt-input.tsx`
- [ ] T011 [P] [US1] Implement workspace state management hook in `frontend/src/hooks/useWorkspace.ts`
- [ ] T012 [US1] Connect prompt submission to `ConversationService` interface in `frontend/src/hooks/useConversation.ts`
- [ ] T013 [US1] Automatically create a new conversation after first prompt in `frontend/src/hooks/useWorkspace.ts`

**Checkpoint**: Prompt workspace fully operational.

---

## Phase 3: User Story 2 — Conversation History (P1)

**Goal**: Users can access previous campaign conversations.

**Independent Test**: Create multiple conversations and switch between them.

### Implementation

- [ ] T014 [US2] Build Recent Conversations sidebar in `frontend/src/components/chat/conversation-list.tsx`
- [ ] T015 [P] [US2] Display conversation titles ordered by latest activity in `frontend/src/components/chat/conversation-item.tsx`
- [ ] T016 [US2] Restore selected conversation in `frontend/src/hooks/useConversation.ts`
- [ ] T017 [P] [US2] Implement New Chat functionality in `frontend/src/hooks/useWorkspace.ts`
- [ ] T018 [US2] Update conversation timestamps after every prompt in `frontend/src/hooks/useConversation.ts`

**Checkpoint**: Conversation history works.

---

## Phase 4: User Story 3 — Company Profile (P1)

**Goal**: Users manage one reusable company profile.

**Independent Test**: Create, edit and delete a company profile.

### Implementation

- [ ] T019 [US3] Build Company Profile page in `frontend/src/components/profile/company-profile.tsx`
- [ ] T020 [P] [US3] Create Company Profile form with React Hook Form + Zod in `frontend/src/components/profile/company-profile.tsx`
- [ ] T021 [US3] Connect `CompanyService` mock implementation in `frontend/src/services/mock/mock-company-service.ts`
- [ ] T022 [US3] Display active company profile inside workspace in `frontend/src/components/layout/workspace.tsx`
- [ ] T023 [US3] Automatically attach active company profile to conversations in `frontend/src/hooks/useConversation.ts`

**Checkpoint**: Company Profile fully functional.

---

## Phase 5: User Story 4 — Campaign Canvas (P1)

**Goal**: Generated campaign assets appear inside an infinite visual canvas.

**Independent Test**: Submit a prompt and verify campaign assets appear inside the canvas.

### Implementation

- [ ] T024 [US4] Build Canvas component in `frontend/src/components/canvas/canvas.tsx`
- [ ] T025 [P] [US4] Create canvas state management hook in `frontend/src/hooks/useCanvas.ts`
- [ ] T026 [P] [US4] Build Campaign Asset components (Image, Caption, Headline, CTA) in `frontend/src/components/canvas/`
- [ ] T027 [US4] Render generated concepts inside the canvas in `frontend/src/components/canvas/canvas.tsx`
- [ ] T028 [US4] Support infinite scrolling as campaign concepts accumulate in `frontend/src/components/canvas/canvas.tsx`

**Checkpoint**: Canvas displays campaign results.

---

## Phase 6: User Story 5 — AI Generation Animation (P2)

**Goal**: Show animated AI workflow while campaigns generate.

**Independent Test**: Submit prompt and verify animation runs before campaign appears.

### Implementation

- [ ] T029 [US5] Build generation animation component in `frontend/src/components/animations/agent-orchestration.tsx`
- [ ] T030 [P] [US5] Build animated workflow timeline in `frontend/src/components/animations/agent-orchestration.tsx`
- [ ] T031 [P] [US5] Display sequential AI generation stages in `frontend/src/components/animations/loading-state.tsx`
- [ ] T032 [US5] Transition automatically from animation to generated campaign in `frontend/src/hooks/useWorkspace.ts`

**Checkpoint**: AI generation animation complete.

---

## Phase 7: User Story 6 — Campaign Refinement (P2)

**Goal**: Users continue refining campaigns using follow-up prompts.

**Independent Test**: Generate campaign then submit follow-up prompt.

### Implementation

- [ ] T033 [US6] Preserve conversation context in `frontend/src/hooks/useConversation.ts`
- [ ] T034 [US6] Append new concepts to existing canvas in `frontend/src/components/canvas/canvas.tsx`
- [ ] T035 [US6] Maintain previous generated assets in `frontend/src/hooks/useCanvas.ts`
- [ ] T036 [US6] Continue generation through `ConversationService` in `frontend/src/hooks/useConversation.ts`

**Checkpoint**: Campaign refinement operational.

---

## Phase 8: Responsive Design

**Purpose**: Optimize UI across desktop, tablet and mobile.

- [ ] T037 Implement responsive sidebar in `frontend/src/components/layout/sidebar.tsx`
- [ ] T038 [P] Implement mobile navigation in `frontend/src/components/layout/mobile-nav.tsx`
- [ ] T039 [P] Optimize prompt workspace for mobile in `frontend/src/components/layout/workspace.tsx`
- [ ] T040 [P] Optimize canvas responsiveness in `frontend/src/components/canvas/canvas.tsx`
- [ ] T041 [P] Validate glassmorphism theme across screen sizes via QA review

**Checkpoint**: Responsive UI completed.

---

## Phase 9: Testing

**Purpose**: Verify all frontend functionality.

### Unit Tests

- [ ] T042 [P] Test Prompt Input component in `frontend/tests/components/chat/prompt-input.test.tsx`
- [ ] T043 [P] Test Conversation List in `frontend/tests/components/chat/conversation-list.test.tsx`
- [ ] T044 [P] Test Company Profile form in `frontend/tests/components/profile/company-profile.test.tsx`
- [ ] T045 [P] Test Canvas rendering in `frontend/tests/components/canvas/canvas.test.tsx`
- [ ] T046 [P] Test mock services in `frontend/tests/services/mock/`
- [ ] T047 [P] Test custom hooks in `frontend/tests/hooks/`

### Integration Tests

- [ ] T048 [P] Test complete prompt workflow in `frontend/tests/integration/prompt-workflow.test.tsx`
- [ ] T049 [P] Test conversation restoration in `frontend/tests/integration/conversation-restoration.test.tsx`
- [ ] T050 [P] Test active company profile attachment during campaign generation in `frontend/tests/integration/company-profile.test.tsx`
- [ ] T051 [P] Test campaign refinement workflow in `frontend/tests/integration/campaign-refinement.test.tsx`

### UI Tests

- [ ] T052 [P] Test responsive layouts in `frontend/tests/ui/responsive-layouts.spec.ts`
- [ ] T053 [P] Test mobile navigation in `frontend/tests/ui/mobile-navigation.spec.ts`
- [ ] T054 [P] Test generation animation in `frontend/tests/ui/generation-animation.spec.ts`
- [ ] T055 [P] Test glassmorphism theme consistency in `frontend/tests/ui/glassmorphism-theme.spec.ts`

**Checkpoint**: Frontend fully tested.

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends On |
|-------|------------|
| Phase 1 (Setup) | — |
| Phase 2 (US1) | Phase 1 |
| Phase 3 (US2) | Phase 1 |
| Phase 4 (US3) | Phase 1 |
| Phase 5 (US4) | Phase 2 |
| Phase 6 (US5) | Phase 5 |
| Phase 7 (US6) | Phase 5 |
| Phase 8 (Responsive) | Phase 2–7 |
| Phase 9 (Testing) | Phase 1–8 |

### Parallel Opportunities

The following tasks can be completed simultaneously:

**Setup (Phase 1)**

- T002, T003, T004, T005, T006, T008

**Workspace (Phase 2)**

- T010, T011

**Conversation (Phase 3)**

- T014, T015, T017

**Company Profile (Phase 4)**

- T019, T020

**Canvas (Phase 5)**

- T025, T026

**Animation (Phase 6)**

- T029, T030, T031

**Testing (Phase 9)**

- T042–T047 (unit tests — all parallel)
- T048–T051 (integration tests — all parallel)
- T052–T055 (UI tests — all parallel)

---

## Parallel Example: User Story 1 — AI Campaign Workspace

```bash
# Launch all parallel tasks for US1 together:
Task: T010  Build prompt input component in frontend/src/components/chat/prompt-input.tsx
Task: T011  Implement workspace state management hook in frontend/src/hooks/useWorkspace.ts

# Then sequential tasks:
Task: T009  Build application shell
Task: T012  Connect prompt submission to ConversationService
Task: T013  Auto-create new conversation after first prompt
```

---

## Implementation Strategy

### MVP

1. Phase 1 (Setup)
2. Phase 2 (US1: AI Campaign Workspace)
3. Phase 3 (US2: Conversation History)
4. Phase 4 (US3: Company Profile)
5. Phase 5 (US4: Campaign Canvas)

Stop and validate.

The application should already support:
- Prompt workspace
- Conversation history
- Company profile
- Canvas rendering

Everything else can be added incrementally.

### Incremental Delivery

1. Complete Setup + US1 → Test independently → MVP demo
2. Add US2 → Test independently → Deploy
3. Add US3 → Test independently → Deploy
4. Add US4 → Test independently → Deploy
5. Add US5, US6 → Polish → Final deploy

### Notes

- Mock services must be accessed only through service interfaces
- Components must never import mock data directly
- UI contains no business logic
- Hooks communicate with services; components never call services directly.
- All new components must support desktop, tablet and mobile layouts
