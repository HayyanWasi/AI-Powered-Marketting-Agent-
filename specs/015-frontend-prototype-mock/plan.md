# Implementation Plan: Frontend Prototype (Mocked Data)

**Branch**: `015-frontend-prototype-mock` | **Date**: 2026-07-19 | **Spec**: specs/015-frontend-prototype-mock/spec.md
**Input**: Feature specification from `specs/015-frontend-prototype-mock/spec.md`

---

## Summary

The Frontend Prototype provides an AI-first marketing workspace built with Next.js and React. Users interact entirely through natural language prompts instead of traditional dashboards or forms.

The application consists of a responsive glassmorphism interface centered around a conversational workspace, visual campaign canvas, conversation history, and company profile management.

This module intentionally uses a Service Adapter Layer with mocked services that implement the same interfaces as the future backend APIs. The UI never accesses mocked data directly, allowing the backend integration to replace only service implementations without requiring UI changes.

---

## Technical Context

**Language/Version**
- TypeScript 5.x
- React 19
- Next.js 15

**Primary Dependencies**
- Next.js
- React
- TailwindCSS
- shadcn/ui
- Framer Motion
- React Hook Form
- Zod

**Storage**
- Mock in-memory services
- Local state
- No backend persistence

**Testing**
- Vitest
- React Testing Library
- Playwright

**Target Platform**
- Modern browsers
- Desktop
- Tablet
- Mobile

**Project Type**
- Frontend
- Mock Prototype

**Performance Goals**

- Initial page <2 seconds
- Prompt interaction <100ms
- Animation begins <500ms
- Fully responsive

**Constraints**

- Mock services only
- No backend dependency
- No business logic
- Components depend only on service interfaces
- Responsive
- Glassmorphism UI
- Mobile-first

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Test-First**: Tests written before implementation? — N/A (frontend prototype; Vitest + RTL used per spec)
- [x] **Clean Code**: Type hints, dataclasses, docstrings, no print statements? — Use TypeScript with strict types
- [x] **KISS/DRY**: No over-engineering, no unnecessary abstractions? — Service interface layer is minimal and justified
- [x] **Fail Gracefully**: Error handling for all external calls? — Mock services handle errors; UI shows fallback states
- [x] **Architecture**: Linear pipeline, no RAG, env-only config? — Frontend-only; no pipeline required
- [x] **Coverage**: >=80% code coverage target? — Targeted
- [x] **Stack**: Uses approved tech stack (FastAPI, Supabase, Next.js, etc.)? — Frontend stack matches constitution (Next.js, React, TypeScript, Tailwind CSS)

No constitutional violations. Feature uses approved frontend stack. Constitution principles adapted appropriately for frontend-only prototype (mock services, no backend pipeline).

---

## Project Structure

### Documentation (this feature)

```text
specs/015-frontend-prototype-mock/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── conversation-service.ts
│   └── company-service.ts
└── tasks.md             # Phase 2 output (NOT created by /sp.plan)

```

### Source Code (repository root)

```text
frontend/
src/
  app/
    page.tsx
  components/
    layout/
      sidebar.tsx
      workspace.tsx
      mobile-nav.tsx
    chat/
      prompt-input.tsx
      conversation-item.tsx
      conversation-list.tsx
    canvas/
      canvas.tsx
      asset-grid.tsx
      image-card.tsx
      caption-card.tsx
      generation-placeholder.tsx
    animations/
      agent-orchestration.tsx
      canvas-transition.tsx
      loading-state.tsx
    profile/
      company-profile.tsx
    ui/
      ...
  hooks/
    useWorkspace.ts
    useConversation.ts
    useCompanyProfile.ts
  services/
    interfaces/
      conversation-service.ts
      company-service.ts
    mock/
      mock-conversation-service.ts
      mock-company-service.ts
  types/
    conversation.ts
    company.ts
    workspace.ts
    campaign.ts
    api.ts
  lib/
    theme.ts
pages/
tests/

```

**Structure Decision**: Frontend-only application following Next.js App Router conventions. Components organized by domain (layout, chat, canvas, animations, profile) with shared UI primitives in `ui/`. Service interfaces in `services/interfaces/`, mock implementations in `services/mock/`.

---

## Architecture

```text
UI Components
        │
        ▼
Workspace Hooks
        │
        ▼
Service Interfaces (e.g., ConversationService)
        │
 ┌──────┴────────┐
 ▼               ▼
Mock Services   Backend APIs (or ApiConversationService in Module 16)

```

Components never know whether data comes from mocked services or production APIs. The Service Adapter Layer provides a clear migration path.

---

## Workspace Layout

```text
──────────────────────────────────────────────
Sidebar
──────────────────────────────────────────────
Logo
+ New Chat
Recent Conversations
Company Profile
Account
Settings
──────────────────────────────────────────────
Workspace
──────────────────────────────────────────────
Active Company Badge
↓
Conversation Canvas
↓
Prompt Input
↓
Status / Generation
──────────────────────────────────────────────

```

---

## Canvas Flow

```text
User Prompt
    │
    ▼
Canvas Opens
    │
    ▼
Generation Animation
    │
    ▼
Campaign Appears
    │
    ▼
User Continues Prompting
    │
    ▼
New Assets Added
    │
    ▼
Conversation Saved

```

---

## Design Decisions

### AI-first interface

Users never fill traditional campaign forms. Everything begins with a prompt.

### Conversation-first workflow

One conversation contains prompts, generated assets, company context, and campaign history. Conversation becomes the primary entity, and Workspace becomes the primary state.

### Infinite Canvas

Generated assets accumulate instead of replacing previous generations. Canvas acts strictly as a visual renderer, not a state owner.

### Sidebar

The sidebar is intentionally minimal. Contains only New Chat, Recent Conversations, Company Profile, Account, Settings. No dashboards. No analytics. No projects.

### Service Adapter Layer

All mocked data is accessed only through service interfaces. Future backend integration replaces only service implementations. UI remains unchanged.

### Responsive Design

Desktop: Persistent sidebar.
Tablet: Collapsible sidebar.
Mobile: Hamburger navigation.
Canvas remains primary focus.

---

## Testing Strategy

### Unit Tests

* Components
* Hooks
* Service interfaces

### State Management Tests

* Workspace state
* Conversation switching
* Generation state
* Mock services

### Integration Tests

* Prompt flow
* Conversation restoration
* Company profile
* Canvas rendering

### UI Tests

* Responsive layouts
* Sidebar navigation
* Mobile navigation
* Canvas interactions

### Animation Tests

* Animation starts
* Animation completes
* Generated content appears

---

## Tradeoffs

### Mock-first Development

Chosen over early backend integration. Reason: Allows UI/UX exploration before backend completion while guaranteeing API compatibility through shared interfaces.

### Service Interface Layer

Chosen over importing mock data directly. Reason: Backend replacement requires changing only service implementations.

### Prompt-first UI

Chosen over dashboard-driven workflow. Reason: Matches the product vision of AI-assisted marketing rather than traditional marketing software.

### Infinite Canvas

Chosen over replacing previous generations. Reason: Supports iterative AI workflows and campaign refinement without losing context.

---

## Complexity Tracking

No constitutional violations. No exceptions required.

```
