# Quickstart: Frontend Prototype (Mocked Data)

## Prerequisites

- Node.js 20+
- npm or pnpm

## Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
cp .env.example .env.local
# or
pnpm install

# Start development server
npm run dev

```

The app opens at `http://localhost:3000`.

## Environment

Create `.env.local`

```env
NEXT_PUBLIC_APP_NAME=Marketing AI
NEXT_PUBLIC_USE_MOCK_SERVICES=true
NEXT_PUBLIC_API_URL=http://localhost:8000/api

```

When backend integration begins, only `NEXT_PUBLIC_USE_MOCK_SERVICES` changes to `false`. This reinforces the service abstraction.

## Directory Structure

```text
frontend/
src/
  app/               # Next.js App Router pages
  components/
  layout/
  chat/
  canvas/
  animations/
  profile/
  ui/            # Shared UI primitives
  hooks/             # Custom React hooks
  lib/               # Utility functions and constants
    utils.ts
    constants.ts
  services/          # Service layer
    interfaces/
  # Conversation and Company service contracts
    mock/            # Mock implementations
  types/             # TypeScript type definitions

```

## Key Commands

```bash
npm run dev          # Start dev server (http://localhost:3000)
npm run build        # Production build
npm run test         # Run unit tests (Vitest)
npm run test:watch   # Run unit tests in watch mode
npm run coverage     # Generate test coverage report
npm run test:e2e     # Run E2E tests (Playwright)
npm run lint         # Lint check
npm run typecheck    # TypeScript type check

```

## Architecture

```text
User
 │
 ▼
React Components
 │
 ▼
Hooks
 │
 ▼
Service Provider
 │
 ├───────────────┐
 ▼               ▼
Mock Service   API Service

```

## Mock Services

All data flows through service interfaces. To replace mocks with real API:

1. Create API implementation in `services/api/`
2. Implement the same interface from `services/interfaces/`
3. Configure the application provider to use the API implementation instead of the mock implementation.

## Glassmorphism Theme

The design system is defined in `tailwind.config.ts`. Key glass utilities:

```css
.glass-panel {
  @apply rounded-xl border border-white/20 bg-white/5 backdrop-blur-lg;
}

.glass-sidebar {
  @apply bg-white/5 backdrop-blur-2xl border-r border-white/10;
}

.glass-canvas {
  @apply bg-gradient-to-br from-white/5 to-transparent;
}

```

## Development Flow

1. Open workspace
2. Enter prompt
3. Canvas opens
4. AI generation animation plays
5. Generated campaign appears
6. Continue conversation with follow-up prompts
7. Conversation automatically appears in Recent Conversations
8. Switch between conversations
9. Edit Company Profile
10. Refreshing the browser resets all in-memory mock data.

## Backend Integration

The frontend has been intentionally designed so that backend integration requires only replacing service implementations.

The following remain unchanged:

* UI Components
* Layout
* Routing
* State Management
* Hooks
* Styling

Only the service layer changes from:

`services/mock/`

to

`services/api/`

```

