# Data Model: Frontend Prototype (Mocked Data)

## Overview

All entities are defined as TypeScript types/interfaces. Data is managed in-memory by mock services. No backend persistence.

---

## Conversation

Represents one complete campaign workspace including all prompts, generated assets, and canvas state.

```typescript
interface Conversation {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  prompts: Prompt[]
  concepts: CampaignConcept[]
  selectedConceptId: string | null
  companyProfileId: string | null
  status: ConversationStatus
}

enum ConversationStatus {
  Idle = 'idle',
  Generating = 'generating',
  Complete = 'complete',
}


```

**Validation rules**:

* `id`: UUID v4
* `title`: Generated from the first user prompt. (first 50 chars max)
* `prompts`: Non-empty after first submission
* `status`: Transition only: Idle → Generating → Complete → Generating → Complete ...

**State transitions**:

```text
Idle → Generating (on prompt submit)
Generating → Complete (on mock generation finish)
Complete → Generating (on follow-up prompt)


```

---

## Prompt

Represents one user message submitted to the AI or the AI's response.

```typescript
interface Prompt {
  id: string
  conversationId: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}


```

**Validation rules**:

* `content`: Minimum 1 character, maximum 2000 characters
* `conversationId`: Must reference an existing Conversation

---

## Campaign Asset

Represents a generated marketing asset (image, caption, copy).

```typescript
interface CampaignAsset {
  id: string
  conceptId: string
  type: AssetType
  text?: string
  imageUrl?: string
  label: string
  createdAt: Date
  metadata: Record<string, unknown>
}

enum AssetType {
  Headline = 'headline',
  Body = 'body',
  Caption = 'caption',
  Image = 'image',
  CTA = 'cta',
}


```

**Validation rules**:

* `type`: Must be one of the AssetType enum values
* `text` / `imageUrl`: At least one must be defined depending on the asset type
* `label`: User-friendly description (e.g., "Summer Sale Headline")
* `metadata`: Flexible key-value store for generation context

---

## Campaign Concept

Container for a batch of generated assets from one generation cycle.

```typescript
interface CampaignConcept {
  id: string
  conversationId: string
  promptId: string
  generatedAt: Date
  assets: CampaignAsset[]
  status: 'generating' | 'completed' | 'failed'
}


```

---

## Generation Session

Represents a single generation execution process for animation and state tracking.

```typescript
interface GenerationSession {
  id: string
  conversationId: string
  startedAt: Date
  completedAt?: Date
  status: 'generating' | 'completed' | 'failed'
  stages: GenerationStage[]
}


```

---

## Company Profile

Persistent company information reused across campaigns.

```typescript
interface CompanyProfile {
  id: string
  companyName: string
  website?: string
  logoUrl?: string
  industry: string
  brandDescription: string
  brandVoice: string
  createdAt: Date
  updatedAt: Date
}


```

**Validation rules**:

* `companyName`: Required, 1-100 characters
* `industry`: Required, 1-100 characters
* `brandDescription`: Optional, max 1000 characters
* `brandVoice`: Optional, max 500 characters

---

## Workspace State

Represents the current mode of the application.

```typescript
type WorkspaceState =
  | { mode: 'idle' }
  | { mode: 'generating'; stage: string; progress: number }
  | { mode: 'active'; conversationId: string }
  | { mode: 'awaiting-prompt' }


```

**State transitions**:

```text
idle → awaiting-prompt (on app load)
awaiting-prompt → generating (on submit)
generating → active (on generation complete)
active → awaiting-prompt (on new chat)
active → generating (on follow-up prompt)


```

---

## Service Interface Contracts

### CampaignService

```typescript
interface CampaignService {
  createConversation(): Promise<Conversation>
  getConversation(id: string): Promise<Conversation>
  listConversations(): Promise<Conversation[]>
  submitPrompt(conversationId: string, content: string): Promise<Conversation>
  getAssets(conversationId: string): Promise<CampaignAsset[]>
}


```

### CompanyProfile

```typescript
interface CompanyProfile {
  getProfile(): Promise<CompanyProfile | null>
  createProfile(
  data: Omit<
    CompanyProfile,
    'id' | 'createdAt' | 'updatedAt'
  >
): Promise<CompanyProfile>
  updateProfile(data: Partial<CompanyProfile>): Promise<CompanyProfile>
  deleteProfile(): Promise<void>
}


```

---

## Entity Relationships

```text
Conversation (1) ──── (N) Prompt
Conversation (1) ──── (N) CampaignConcept
Conversation (1) ──── (N) GenerationSession
CampaignConcept (1) ──── (N) CampaignAsset
CampaignConcept (1) ──── (1) Prompt
Conversation (N) ──── (0..1) CompanyProfile


```

```

```