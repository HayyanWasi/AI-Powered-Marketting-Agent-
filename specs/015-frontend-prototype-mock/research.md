# Research: Frontend Prototype (Mocked Data)

## Technology Decisions

### Framework: Next.js 15 with App Router

- **Decision**: Next.js 15 with App Router
- **Rationale**: Aligns with existing project tech stack per constitution.App Router is used for routing and layouts. Interactive features (workspace, canvas, prompt input, animations) are implemented as client components., file-based routing, and React Server Components for optimal performance. Client components used only where interactivity is needed (canvas, prompt input, animations).
- **Alternatives considered**: Vite + React (simpler but no SSR), Remix (different routing model)

### UI Components: shadcn/ui

- **Decision**: shadcn/ui for base UI primitives (buttons, inputs, dialogs, cards)
- **Rationale**: Copy-paste components that are fully customizable with TailwindCSS. No external dependency — components live in the codebase. Fits the glassmorphism requirement since every component can be restyled.
- **Alternatives considered**: Headless UI (more primitive), Radix Primitives (lower level), MUI (too opinionated, heavy)

### Animation: Framer Motion

- **Decision**: Framer Motion for canvas animations and UI transitions
- **Rationale**: Industry standard for React animations. Handles layout animations, gesture-based interactions, and sequence-based animations (generation stages).
- **Alternatives considered**: CSS animations (limited sequencing), React Spring (less ecosystem), GSAP (imperative, not React-idiomatic)

### Forms: React Hook Form + Zod

- **Decision**: React Hook Form for form state, Zod for schema validation
- **Rationale**: Lightweight, performant (uncontrolled inputs), pairs naturally with Zod for type-safe validation. Used for Company Profile form.
- **Alternatives considered**: Formik (more verbose, larger bundle), plain useState (no validation)

### Styling: TailwindCSS

- **Decision**: TailwindCSS for all styling
- **Rationale**: Already in project stack. Utility-first approach enables rapid prototyping and consistent design tokens. Glassmorphism effects (backdrop-blur, bg-opacity, border-glass) are native Tailwind utilities.
- **Alternatives considered**: Styled Components (runtime CSS-in-JS), CSS Modules (no design token system)

### Testing: Vitest + React Testing Library + Playwright

- **Decision**: Vitest (unit), React Testing Library (component), Playwright (E2E)
- **Rationale**: Vitest provides fast unit testing with good TypeScript support.RTL enforces testing from user perspective. Playwright for responsive visual regression testing.
- **Alternatives considered**: Jest (slower), Cypress (different philosophy, heavier)

### Type Safety: TypeScript 5.x with strict mode

- **Decision**: TypeScript strict mode enabled
- **Rationale**: Catches null/undefined errors at compile time. Ensures service interface contracts are type-checked.
- **Alternatives considered**: JavaScript with JSDoc (less safe), Flow (deprecated ecosystem)

### Service Layer Pattern: Interface-based dependency injection

- **Decision**: Service interfaces defined as TypeScript interfaces, implemented by mock services and consumed through custom hooks., implemented by mock services, consumed by custom hooks
- **Rationale**: Allows drop-in replacement of mock services with real API implementations. Components and hooks depend only on interfaces, not implementations.
- **Alternatives considered**: Direct mock data imports (tight coupling), Context API service provider (more ceremony)

### State Management: Custom hooks + React state

- **Decision**: Custom hooks (useWorkspace, useConversation, useCompanyProfile) using React useState/useReducer
- **Rationale**: Sufficient for prototype complexity. No external state library needed. Hooks encapsulate service calls and local state.
- **Alternatives considered**: Zustand (external dependency), Redux (overkill), Jotai (unnecessary for this scale)

### Responsive Strategy: Mobile-first with Tailwind breakpoints

- **Decision**: Mobile-first CSS using Tailwind breakpoints (sm: 640px, md: 768px, lg: 1024px)
- **Rationale**: Mobile-first aligns with spec requirement. Sidebar collapses into a mobile navigation pattern below md breakpoint. at md breakpoint. Canvas stays full-width at all sizes.
- **Alternatives considered**: Desktop-first (harder mobile adaptation), CSS Grid auto-fit (less control)

## Integration Patterns

### Mock Service Contract

```typescript
interface CampaignService {
  createConversation(): Promise<Conversation>
  getConversation(id: string): Promise<Conversation>
  listConversations(): Promise<Conversation[]>
  submitPrompt(
    conversationId: string,
    content: string
  ): Promise<Conversation>
  getAssets(conversationId: string): Promise<CampaignAsset[]>
}

interface CompanyService {
  getProfile(): Promise<CompanyProfile | null>

  createProfile(
    data: Omit<
      CompanyProfile,
      'id' | 'createdAt' | 'updatedAt'
    >
  ): Promise<CompanyProfile>

  updateProfile(
    data: Partial<CompanyProfile>
  ): Promise<CompanyProfile>

  deleteProfile(): Promise<void>
}
```

### Data Flow

User Action → Component → Hook → Service Interface → Mock Service → Hook State → Component Re-render

## Performance Estimates

| Metric | Target | Method |
|--------|--------|--------|
| Initial page load | <2s | Next.js static generation + code splitting |
| Prompt submit to animation start | <500ms | No network call; mock service returns immediately |
| Animation duration | 2-3s | Simulated delay for UX feel |
| Conversation switch | <500ms | In-memory state swap |
| Canvas scroll | 60fps | Efficient React rendering and lazy image loading |

## Glassmorphism Design Tokens

- Background: `bg-white/10 backdrop-blur-xl` (light), `bg-black/20 backdrop-blur-xl` (dark)
- Card/panel: `rounded-xl border border-white/20 bg-white/5 backdrop-blur-lg`
- Sidebar: `bg-white/5 backdrop-blur-2xl border-r border-white/10`
- Canvas: `bg-gradient-to-br from-white/5 to-white/0`
- Text: Primary on glass surfaces needs sufficient contrast — use `text-white/90` on dark, `text-gray-900/90` on light
