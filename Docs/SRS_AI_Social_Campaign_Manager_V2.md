# Software Requirements Specification (SRS)

**Project:** AI Social Campaign Manager (V1)

**Version:** 2.0

**Document Version:** Final

---

# Table of Contents

1. Introduction
   - Purpose
   - Scope
   - Definitions
2. Overall Description
   - Product Perspective
   - User Characteristics
   - Operating Environment
   - Design Constraints
3. Technology Stack
4. System Architecture
5. Workflow Overview
6. Functional Requirements
   - Conversation Module
   - Company Profile Module
   - Data Enrichment Module
   - Session Cache Module
   - AI Orchestration Module
   - Agent-Based Campaign Generation
   - Image Generation
   - Validation
   - Human Review
   - Publishing
7. Non-Functional Requirements
8. External Interface Requirements
9. Success Criteria
10. Future Enhancements (V2)

---

# 1. Introduction

## 1.1 Purpose

This document outlines the requirements for an AI-powered social media content generation system designed for event marketing teams. The system automates the creation of branded posts for event speakers/guests by combining live web research, brand style conditioning, and multi-prompt AI orchestration—eliminating manual content creation across multiple post types (Seminar, Contest, Community Gathering, Test Result, Course Announcement, Entry Test).

## 1.2 Scope

Version 1 includes:

- Chat-based campaign creation
- Live guest information retrieval using DDGS
- Session-based guest data storage
- Company profile management
- AI-generated captions
- AI-generated campaign images
- Validation checks
- Human approval workflow
- Publishing or scheduling

## 1.3 Definitions

| Term | Description |
|------|-------------|
| LLM | Large Language Model |
| DDGS | duckduckgo-search library |
| Agent | AI component responsible for generating a specific campaign type |
| Orchestrator | LangGraph workflow that coordinates agents |
| Brand Kit | Company guidelines and reference images |

---

# 2. Overall Description

## Product Perspective

The system is an AI-assisted campaign generation platform built around an agent-based architecture managed by LangGraph.

## User Characteristics

- **Primary User:** Marketing organizers, event managers, or content creators.
- **Technical Level:** Low-to-medium. The user interacts purely via a chat-based interface; they do not write code or manage infrastructure.
- **Pain Point:** Currently spending 2-3 hours manually researching guests, drafting copy, and designing images per post.

## Operating Environment

- Web application
- FastAPI backend
- Next.js frontend
- Cloud-hosted services

## Design Constraints

- Guest data must never be permanently stored.
- Company data is stored in PostgreSQL.
- Brand images are stored in Cloudinary.
- Live search uses DDGS.
- No scraping of restricted social media platforms.

---

# 3. Technology Stack

| Layer | Technology |
|--------|------------|
| Frontend | Next.js 14+ (App Router) + React 18+ + TypeScript 5+ |
| UI Framework | Tailwind CSS 3+ + shadcn/ui components |
| State Management | React Context API + Zustand (for chat state) |
| API Client | TanStack Query (React Query) for server state |
| Backend | FastAPI (Python 3.10+) |
| AI Orchestrator | LangGraph |
| Agent Framework | LangChain |
| Database | PostgreSQL (Supabase) |
| Session Cache | Python Memory (V1), Redis (Production) |
| Search | duckduckgo-search (DDGS) |
| Image Generation | Pollinations AI |
| Image Storage | Cloudinary |
| LLM | OpenAI GPT-4o / Google Gemini |
| Deployment | Docker + VPS |

---

# 4. System Architecture

```text
User
   │
   ▼
Next.js Chat UI
   │
   ▼
FastAPI Backend
   │
   ▼
LangGraph Orchestrator
   │
   ├── Seminar Agent
   ├── Contest Agent
   ├── Community Gathering Agent
   ├── Course Announcement Agent
   ├── Entry Test Agent
   └── Test Result Agent
   │
   ▼
DDGS / LLM / Pollinations / Cloudinary

Each campaign type is implemented as an independent LangChain-based sub-agent. The LangGraph orchestrator selects the correct agent based on the campaign type.

---

# 5. Workflow Overview

```text
Start
 ↓
Collect Campaign Information
 ↓
Search Guest Information (DDGS)
 ↓
Search Success?
 ├── Yes → Cache Guest Data
 └── No  → Ask User for Manual Bio
 ↓
Load Company Profile
 ↓
Select Campaign Agent
 ↓
Generate Caption
 ↓
Generate Image
 ↓
Validate
 ↓
Preview
 ↓
Human Approval
 ├── Reject → Regenerate
 └── Approve → Publish
```

---

# 6. Functional Requirements

## 6.1 Conversation Module

- FR-01: The system shall collect guest data via a step-by-step conversational interface (not a form).
- FR-02: The system shall first ask: "What is your guest and company name?" and wait for user response.
- FR-03: Upon receiving name + company, the system shall call duckduckgo-search (ddgs) to fetch web snippets.
## 6.2 Company Profile Module

- FR-04: A rate limiter (min 5-second delay between calls) and 15-second timeout must be enforced on all ddgs calls.
- FR-05: If ddgs returns results, the system shall extract: Name, Title, Company, 50-word Bio.
- FR-06: If ddgs returns no results or times out, the system shall fallback to: "Couldn't fetch automatically. Please type guest's title and 2-line bio."

## 6.3 Data Enrichment Module

- FR-07: Guest data shall be stored in in-memory session cache (not database) for the current session/event. Cache expires after 24 hours or session end.
- FR-08: After guest data collection, the system shall ask: "Which post type you want?" with options: Seminar, Contest, Community Gathering, Test Result, Course Announcement, Entry Test.
- FR-09: The system shall use 1 orchestrator that routes to 6 different system prompts (one per post type). These are NOT separate code pipelines—just different prompts.

## 6.4 Session Cache Module

- FR-10: Each system prompt shall define: tone, structure, image style hint, and call-to-action format for that post type.
- FR-11: During company setup, the user shall upload 5-6 brand reference images (logo, color palette, style examples) via the chat interface.
## 6.5 AI Orchestration Module

- FR-12: The system shall upload these images to Supabase Storage (public bucket) and generate permanent public URLs.
- FR-13: The URLs + brand tone + company name shall be stored in Supabase Database company_profiles table.
- FR-14: During content generation, the system shall fetch the primary reference image URL from DB and pass it to Pollinations image parameter for style conditioning.

## 6.6 Agent-Based Campaign Generation

- FR-15: NOTE: This is NOT RAG or vector embeddings—it's simple key-value lookup by company_id.
- FR-16: The system shall generate text (caption, hook, hashtags) using LLM (Gemini/GPT) with the selected system prompt + guest data + brand tone.
- FR-17: The system shall generate an image using Pollinations AI (kontext model) with: prompt = description from LLM, image = brand reference URL from DB.
- FR-18: Both text and image generation shall happen in parallel (or sequentially, based on API constraints).

## 6.7 Image Generation

- FR-19: Character Limit Check: Generated caption must be validated against platform limits: LinkedIn ≤3000, Instagram ≤2200. If exceeded, system shall warn user with: "Caption exceeds X platform limit by Y characters. Please edit before publishing."
- FR-20: Image Resolution Check: Generated image must be ≥1080x1080 pixels. If lower, system shall reject and regenerate automatically.

## 6.8 Validation

- FR-21: Preview Node: The system shall display the complete post (text + image) to the user.
- FR-22: Human Approval Gate: The post shall NOT be scheduled/published unless user clicks "Approve". User may click "Reject" to regenerate or edit.
- FR-23: Note: Bias/inconsistency checks and sentiment feedback loops are deferred to V2.

## 6.9 Human Review

- FR-24: Upon user approval, the system shall proceed to scheduling/publishing.
- FR-25: V1: Publishing via official platform APIs (LinkedIn/Instagram) if OAuth setup is completed, OR manual copy-paste fallback.
## 6.10 Publishing

- FR-26: Future: Multiple posts can be scheduled on a multi-day calendar (V2).

---

# 7. Non-Functional Requirements

- Performance: End-to-end generation (text + image) shall complete within 60 seconds for single post.
- Reliability: If ddgs or Pollinations fails, system must gracefully display user-friendly error and offer manual fallback.
- Availability:	Target 99.5% uptime (excluding third-party API outages).
- Security:	All API keys (LLM, Pollinations, Supabase) stored as environment variables. No hardcoding.
- Data Retention:	Guest data is ephemeral—stored only in session cache, never persisted to DB.

---

# 8. External Interface Requirements

## User Interface

- Chat-based interface built with React + Next.js
- Brand image upload with drag-and-drop support
- Campaign preview with generated text + image
- Approve / Reject actions with visual feedback

## Third-Party Services

- OpenAI GPT-4o or Google Gemini
- Pollinations AI
- Cloudinary
- DDGS

---
# 9.1 Framework & Backend

Language: Python 3.10+

Web Framework: FastAPI (lightweight, async support)

Orchestration: Custom Python logic (LangGraph NOT required for V1 linear pipeline)

5.2 Database & Storage

Database: Supabase (PostgreSQL) for company profiles + brand guidelines

Storage: Supabase Storage (public bucket) for brand reference images

Session Cache: Python functools.lru_cache or simple dict per session

5.3 AI & APIs

LLM: OpenAI GPT-4o or Google Gemini (via SDK)

Image Generation: Pollinations AI (kontext model) with image parameter for style conditioning

Web Search: duckduckgo-search (ddgs) with rate limiter + timeout

Image Validation: Pillow (PIL) for resolution checks

5.4 Deployment

Containerization: Docker

Hosting: VPS (DigitalOcean, AWS EC2, or Google Cloud Run)

---
# 9. Success Criteria

The project will be considered successful if it meets the following criteria:

1. Generate realistic and professional-looking social media campaign previews.	User acceptance test: ≥90% users rate preview as "professional"
2. Include a sentiment analysis mechanism that helps evaluate audience reaction so future AI conversations and prompts can be improved.	Deferred to V2
3. Produce marketing content that contains a strong audience engagement or call-to-action statement.	Each generated post includes at least 1 CTA (measured by automated check)
4. Reduce repetitive AI outputs by encouraging varied responses and minimizing repeated wording or inherited bias from training data.	Deferred to V2
5. Ensure every generated campaign image meets the required resolution for social media publishing.	100% of images pass ≥1080x1080 resolution check
6. Ensure every campaign agent follows the required advertisement or campaign format consistently.	100% of generated posts pass character limit check for target platform
7.  Maintain company branding throughout generated captions and images.	Manual QA: 95% of posts use brand tone + reference image style
8. Require human approval before any campaign is published.	Zero posts published without explicit "Approve" click

---

# 10. Future Enhancements (V2)

- Bias detection
- Sentiment feedback loop
- Social platform APIs
- Analytics dashboard
- Multi-user collaboration
- Redis distributed cache
- Campaign history
- AI memory
- Additional campaign agents
