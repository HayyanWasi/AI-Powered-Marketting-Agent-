# Feature Specifications for AI Social Campaign Manager

Based on the SRS, I've broken down the project into **19 feature specifications** that align with the functional requirements. Each feature is a self-contained unit that can be developed, tested, and delivered independently.

---

## Feature Specification List

### 1. `project-foundation` - Project Setup & Configuration
**Phase: Foundation**

**Description:** Initialize the project with UV package manager, configure development tools, and establish the foundational project structure.

**Functional Requirements Covered:** None directly (infrastructure)

**Key Components:**
- UV project initialization with `pyproject.toml`
- Development tools: Black, Ruff, mypy, pytest
- Environment variables management
- Docker configuration
- Git hooks for pre-commit checks

**Acceptance Criteria:**
- `uv run python -c "import fastapi"` works without errors
- All linting, formatting, and type checking pass
- Docker builds successfully
- Environment variables load from `.env` fi

---

### 2. `database-storage` - Database & Storage Setup
**Phase: Foundation**

**Description:** Set up Supabase PostgreSQL database and storage buckets for company profiles and brand images.

**Functional Requirements Covered:** FR-11, FR-12, FR-13

**Key Components:**
- `company_profiles` table schema
- Supabase Storage public bucket
- CRUD operations for company profiles
- Image upload and URL generation
- Database migration scripts

**Acceptance Criteria:**
- Company profile can be created/read/updated/deleted
- Images upload to Supabase Storage with public URLs
- Database operations have ≥80% test coverage
- Migration scripts work both up and down

---

### 3. `session-cache` - Session Cache System
**Phase: Foundation**

**Description:** Implement in-memory session cache for ephemeral guest data storage with 24-hour TTL.

**Functional Requirements Covered:** FR-07

**Key Components:**
- In-memory cache using Python dict
- TTL mechanism (24-hour expiry)
- Session ID generation
- Cache cleanup utilities
- Concurrent session handling

**Acceptance Criteria:**
- Guest data expires after 24 hours
- Multiple concurrent sessions work independently
- Cache can be manually cleared
- Tests cover all edge cases (expiry, concurrent access)

---

### 4. `data-models` - Data Models & Schemas
**Phase: Core Services**

**Description:** Define all data structures as Python dataclasses and Pydantic schemas with validation.

**Functional Requirements Covered:** FR-05, FR-10

**Key Components:**
- `Guest` dataclass: name, title, company, bio
- `Campaign` dataclass: type, caption, image_url, status
- `Company` dataclass: id, name, tone, reference_image_urls
- Pydantic schemas for API validation
- Type hints and validation decorators

**Acceptance Criteria:**
- All models pass mypy strict mode
- Validation catches invalid data
- Models serialize/deserialize correctly
- 100% test coverage for models

---

### 5. `ddgs-service` - DuckDuckGo Search Service
**Phase: Core Services**

**Description:** Implement web search service using duckduckgo-search library with rate limiting and timeout.

**Functional Requirements Covered:** FR-03, FR-04, FR-05, FR-06

**Key Components:**
- DDGS wrapper with search function
- Rate limiter (5-second minimum)
- Timeout mechanism (15 seconds)
- Data extraction: Name, Title, Company, Bio
- Fallback handling for no results/timeout
- Mock for testing

**Acceptance Criteria:**
- Search returns structured guest data
- Rate limiting enforced (min 5s between calls)
- Timeout triggers fallback after 15s
- Graceful error handling with user-friendly messages
- 100% test coverage on success/failure paths

---

### 6. `llm-service` - LLM Integration Service
**Phase: Core Services**

**Description:** Implement unified interface for OpenAI GPT-4o and Google Gemini LLMs with system prompt management.

**Functional Requirements Covered:** FR-16

**Key Components:**
- OpenAI GPT-4o client
- Google Gemini client
- Unified interface (supports both providers)
- System prompt injection
- Retry logic with exponential backoff
- Token counting utilities
- Mock for testing

**Acceptance Criteria:**
- Both providers work with same interface
- System prompts correctly injected
- Retry logic handles API failures
- Tests with mocks pass
- Error handling provides meaningful feedback

---

### 7. `pollinations-service` - Image Generation Service
**Phase: Core Services**

**Description:** Implement Pollinations AI integration for campaign image generation with brand style conditioning.

**Functional Requirements Covered:** FR-14, FR-17

**Key Components:**
- Pollinations API client
- `kontext` model integration
- Brand reference image URL parameter
- Prompt construction from LLM description
- Image URL validation
- Error handling and retries
- Mock for testing

**Acceptance Criteria:**
- Generates image with brand style from reference
- Image URL is valid and accessible
- API failures handled gracefully
- Tests with mocks pass

---

### 8. `validation-service` - Content Validation Service
**Phase: Core Services**

**Description:** Implement validation checks for character limits and image resolution.

**Functional Requirements Covered:** FR-19, FR-20

**Key Components:**
- Character limit checker (LinkedIn: 3000, Instagram: 2200)
- Image resolution checker using Pillow (≥1080x1080)
- Auto-regeneration trigger for resolution failures
- Validation error reporting with clear messages
- Platform-specific limit configuration

**Acceptance Criteria:**
- Character limits enforced correctly
- Resolution check works for images
- Auto-regeneration triggered for resolution failures
- Clear error messages shown to user

---

### 9. `company-service` - Company Profile Service
**Phase: Business Logic**

**Description:** Implement company profile management with brand image upload and retrieval.

**Functional Requirements Covered:** FR-11, FR-12, FR-13, FR-15

**Key Components:**
- Company CRUD operations
- Brand image upload (5-6 images)
- Image URL storage in database
- Key-value lookup by company_id
- Brand tone management
- Reference image URL retrieval

**Acceptance Criteria:**
- Company profile created with name and tone
- 5-6 brand images uploaded with public URLs
- Fast key-value lookup (<100ms)
- All tests pass with real Supabase

---

### Module 10. — Campaign Management

Responsibility: Everything related to campaigns from the business perspective.

Campaign Module
│
├── Campaign CRUD
├── Campaign Configuration
├── Campaign Goals
├── Platform Selection
├── Audience Selection
├── Campaign History
├── Campaign Status
├── Publish
└── Analytics (future)

This module doesn't know AI exists.



final results and Architecture:
```

Architecture Enforced
Context Builder ──▶ GenerationContext (immutable)
                          │
                    ┌─────┴─────┐
                    │ Orchestrator│
                    └─────┬─────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
Reference Matcher    Strategy Agent      Campaign Planner
    │                     │                     │
    └─────────────────────┼─────────────────────┘
                          │
              Content Generation Agent
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    Hook Analyzer   Hashtag Research   Readability Scorer
         │                │                │
         └────────────────┼────────────────┘
                          │
                   Validation Agent
                          │
                  Asset Generation Agent
                          │
                    [PUBLISH]
Key Rule Enforced
GenerationContext is immutable. No agent reads from database during execution. All data flows through the context snapshot.

### Files Created

| File | Purpose |
| --- | --- |
| `src/agents/__init__.py` | Package init |
| `src/agents/context.py` | GenerationContext + data models (BrandData, GuestData, EventData, StrategyData, ContentSlot, ContentDraft, ValidationResult) |
| `src/agents/base.py` | BaseAgent abstract class + AgentResult |
| `src/agents/context_builder.py` | Creates GenerationContext from input data (reads DB once) |
| `src/agents/orchestrator.py` | Workflow coordinator – runs agents in sequence, handles approval/rejection |
| `src/agents/reference_matcher.py` | Loads brand data into context |
| `src/agents/strategy.py` | Generates marketing strategy brief (LLM) |
| `src/agents/campaign_planner.py` | Builds content calendar grid |
| `src/agents/content_generator.py` | Writes 3 copy variants per slot (LLM) |
| `src/agents/asset_generator.py` | Generates images via Pollinations.ai |
| `src/agents/validator.py` | Validates content against platform rules |
| `src/agents/subagents/__init__.py` | Sub-agents package |
| `src/agents/subagents/hook_analyzer.py` | Scores hooks for scroll-stopping power |
| `src/agents/subagents/hashtag_research.py` | Finds trending hashtags |
| `src/agents/subagents/readability_scorer.py` | Flesch reading ease score |
| `tests/unit/test_orchestrator.py` | 13 tests for orchestrator + context |
```
---
### Module 11 — AI Generation Engine

This is the heart of the AI.

AI Generation Module
│
├── Context Builder
├── Strategy Planner
├── Copy Generator
├── Image Prompt Editor
├── Image Generator
├── Validation
└── Intent Analyzer

Notice:

Everything here is about creating content.

Nothing about workflow.

Nothing about retries.

Nothing about history.

Just generation.
---
### Module 12 — Workflow Engine

This is where LangGraph belongs.

Workflow Module
│
├── Graph Definition
├── State Management
├── Node Routing
├── Conditional Routing
├── Retry
├── Resume
├── Human Approval
├── Checkpoints
└── Execution Control

This module should know nothing about marketing.

It only knows

Execute Node A → Node B → Node C.

This is the biggest separation I would make.

---
### Module 13 — Platform & Operations

Everything production-related.

Operations Module
│
├── Observability
├── Tracing
├── Logging
├── Metrics
├── Prompt Versioning
├── Model Versioning
├── Cost Tracking
├── Token Tracking
├── Performance Monitoring
├── Guardrails
├── Execution History
└── Evaluation (future)

This module never generates content.

It watches everything.
---
### 11. `orchestrator-pipeline` - Orchestrator Linear Pipeline
**Phase: Business Logic**

**Description:** Implement the linear workflow orchestration connecting all services.

**Functional Requirements Covered:** FR-01, FR-02, FR-08, FR-09, FR-16, FR-17, FR-18, FR-21, FR-22

**Key Components:**
- Conversation flow management:
  1. Ask for guest name + company
  2. Search DDGS (with fallback)
  3. Cache guest data
  4. Ask for post type
  5. Select agent
  6. Generate caption + image (parallel)
  7. Validate
  8. Preview
  9. Approval gate
  10. Publish
- Async parallel execution
- Error handling for each step
- Session state management
- Logging and monitoring

**Acceptance Criteria:**
- Complete workflow runs end-to-end
- Error scenarios handled gracefully
- Completion time ≤60 seconds
- All FRs implemented correctly
- Tests cover all scenarios

---

### 12. `fastapi-routes` - FastAPI REST API
**Phase: Integration**

**Description:** Implement REST API endpoints for all system functionality with OpenAPI documentation.

**Functional Requirements Covered:** All FRs (exposed via API)

**Key Components:**
- Route handlers:
  - `GET /api/company/{id}`
  - `POST /api/company`
  - `PUT /api/company/{id}`
  - `POST /api/company/{id}/brand-images`
  - `POST /api/campaign/generate`
  - `POST /api/campaign/{id}/approve`
  - `POST /api/campaign/{id}/reject`
  - `POST /api/campaign/{id}/publish`
  - `GET /api/session/guest`
  - `POST /api/session/guest`
  - `DELETE /api/session`
  - `GET /api/session/status`
- Dependency injection
- Error handling middleware
- CORS configuration
- OpenAPI docs at `/docs`
- Health check endpoint

**Acceptance Criteria:**
- All endpoints work correctly
- Swagger docs available and accurate
- Proper error responses with HTTP status codes
- CORS configured for frontend
- Tests for all endpoints

---
---

## Module 13 — Platform & Operations

**Phase:** Infrastructure

**Description:** Centralized operational services responsible for monitoring, tracing, logging, execution history, model management, and production observability. This module never participates in campaign generation or workflow decisions.

**Responsibilities:**

- Observability
- Structured Logging
- Distributed Tracing
- Metrics Collection
- Cost Tracking
- Token Usage Tracking
- Prompt Versioning
- Model Versioning
- Performance Monitoring
- Guardrails
- Execution History
- Evaluation Framework (Future)

**Key Rule**

This module never generates content.

It only observes, measures, records, and protects the system.

---

## Module 14 — API Layer

**Phase:** Integration

**Description:** Public REST API exposing the system to frontend applications while delegating all business logic to internal modules.

**Responsibilities**

- FastAPI Routes
- Request Validation
- Response Serialization
- Authentication
- Dependency Injection
- API Documentation
- Error Translation

---

## Module 15 — Frontend

**Phase:** User Experience

**Description:** Next.js frontend responsible only for user interaction.

**Responsibilities**

- Chat Interface
- Campaign Builder
- Campaign Review
- Human Approval UI
- Company Profile Management
- Dashboard
- Authentication
- API Integration

---

## Module 16 — Deployment & Infrastructure

**Phase:** Production

**Description:** Infrastructure required to build, deploy, monitor, and operate the application.

**Responsibilities**

- Docker
- CI/CD
- Environment Configuration
- Health Checks
- Backup Strategy
- Rollback
- Infrastructure Automation

---

## Module 17 — Documentation

**Phase:** Documentation

**Description:** Project documentation for developers, operators, and contributors.

**Responsibilities**

- README
- API Documentation
- Architecture Documentation
- Deployment Guide
- Development Guide
- ADRs
- Troubleshooting