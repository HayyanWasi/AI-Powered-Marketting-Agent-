# AI Marketing Automation System — System Overview

---

## 1. Problem Statement

Event marketing today is bottlenecked by manual, fragmented workflows that degrade content quality and lower conversion rates:

*   **Information Silos:** Brand assets, guest details, and event logistics are scattered across emails, spreadsheets, and chat groups, leading to manual copy-paste errors and inconsistent brand tone.
*   **Time-Intense Guest Research:** Generating speaker profiles and marketing cards requires manual searching, scraping, and writing, which takes hours per guest.
*   **API Walls & Setup Overhead:** Standard web scrapers are frequently blocked by LinkedIn/Instagram login screens, requiring complex headless browser maintenance.
*   **Formatting & Platform Errors:** Writing raw copy before assigning it to a platform leads to character overflows (e.g., Twitter's 280-character limit) or visual formatting issues on publishing.
*   **Lack of Tracking:** Teams struggle to track impressions and clicks cleanly across multiple networks, preventing them from understanding what content actually drives registrations.

The business impact is **declining audience engagement, lower attendance rates, and significant time wasted on repetitive operations.**

---

## 2. Solution

The **AI Marketing Automation System** is an autonomous, multi-agent pipeline orchestrated to handle end-to-end event marketing with zero operational friction:

1.  **Unified Ingestion:** A one-time PDF upload stores long-term brand tone in a semantic search vector index, while a simple 2-minute form tracks structured event parameters (dates, links, platforms, guest URLs).
2.  **Autonomous Guest Research:** An iterative search engine agent bypasses login walls by scraping search snippets to build fact-verified, reputation-based speaker cards without human effort.
3.  **Human-Approved Strategy:** The system acts as a virtual CMO, generating a Strategy Brief (USP, messaging pillars, objection handling) that must be approved by the user before content planning begins.
4.  **Planning-First Scheduling:** Before writing copy, the system builds the calendar grid, ensuring that the Content Generator writes platform-native copy matching specific character limits (LinkedIn, Instagram, Twitter/X).
5.  **Branded Asset Generation:** Generates conceptual backgrounds via free image APIs and programmatically overlays speaker portraits, organization logos, and text elements at $0 cost.
6.  **Automatic Publishing & Metrics Tracking:** Pushes approved campaigns directly to social media queues and syncs engagement metrics (impressions, clicks, interactions) back to a unified Streamlit dashboard.

---

## 3. Architecture

This diagram illustrates the logical interaction between the User Interface, the Hybrid Storage layers, the Agent nodes, and free external API integrations.

```mermaid
flowchart LR
    %% Styling
    classDef input fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef stage1 fill:#0369a1,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef stage2 fill:#4338ca,stroke:#818cf8,stroke-width:2px,color:#fff;
    classDef stage3 fill:#c2410c,stroke:#fb923c,stroke-width:2px,color:#fff;
    classDef stage4 fill:#065f46,stroke:#34d399,stroke-width:2px,color:#fff;
    classDef user fill:#831843,stroke:#f43f5e,stroke-width:2px,color:#fff;
    classDef storage fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff;

    UserBrief(["👤 Marketer Input\n(Goal, Speakers, Brand)"]):::input

    %% ─────────────────────────────────────────────────────────────
    %% STAGE 1: INTAKE & RESEARCH
    %% ─────────────────────────────────────────────────────────────
    subgraph S1 ["1. Intake & Live Intelligence"]
        direction TB
        ExaBio["🔎 Exa Semantic Search\n(Speaker Bios & Credentials)"]:::stage1
        DDGTrends["🌐 DuckDuckGo & Neo4j\n(Market & Competitor Trends)"]:::stage1
        ExaBio ~~~ DDGTrends
    end

    %% ─────────────────────────────────────────────────────────────
    %% STAGE 2: CAMPAIGN PLAN (PANEL FAN-OUT & REFINEMENT)
    %% ─────────────────────────────────────────────────────────────
    subgraph S2 ["2. Campaign Plan (LangGraph Panel Fan-Out)"]
        direction TB
        PlanStart(["start"]):::stage2
        
        subgraph PanelFanOut ["5 Parallel Specialists"]
            direction TB
            Audience["audience_research"]:::stage2
            Channel["channel_plan"]:::stage2
            Measurement["measurement"]:::stage2
            Positioning["positioning"]:::stage2
            Competitive["competitive_analysis"]:::stage2
        end

        Synthesize["synthesize\n(Chief Strategist)"]:::stage2
        PlanRefine["🔄 Plan Refinement Agent\n(Revise · Apply · Reply)"]:::stage2
        HITLReview{{"🙋 Human Approval\n(Review & Approve Plan)"}}:::user

        PlanStart --> Audience & Channel & Measurement & Positioning & Competitive
        Audience & Channel & Measurement & Positioning & Competitive --> Synthesize
        Synthesize --> HITLReview
        HITLReview <-->|"Interactive Revisions"| PlanRefine
    end

    ContextSnapshot["🧱 Context Builder\n(Locks Brand, Speaker\n& Strategy Snapshot)"]:::input

    %% ─────────────────────────────────────────────────────────────
    %% STAGE 3: CREATIVE STUDIO (COPY & 9:16 VIDEO REELS)
    %% ─────────────────────────────────────────────────────────────
    subgraph S3 ["3. Creative Studio (Posts + Video)"]
        direction TB
        
        subgraph S3A ["📝 Thought-Leadership Copy"]
            direction TB
            CopyGen["AI Copywriter\n(LinkedIn Posts)"]:::stage3
            HookEval["Hook & Retention Analyzer"]:::stage3
            HashEval["Hashtag Optimization"]:::stage3
            ReadEval["Readability & Cadence Scorer"]:::stage3

            CopyGen --> HookEval --> HashEval --> ReadEval
        end

        subgraph S3B ["🎬 9:16 Video Reel Studio"]
            direction TB
            VideoScript["Video Script Agent"]:::stage3
            PollinationsScenes["Pollinations AI (Scenes)"]:::stage3
            TTSVoice["Edge-TTS (Voiceover)"]:::stage3
            MoviePyStitcher["MoviePy Video Stitcher"]:::stage3

            VideoScript --> PollinationsScenes
            VideoScript --> TTSVoice
            PollinationsScenes --> MoviePyStitcher
            TTSVoice --> MoviePyStitcher
        end
    end

    %% ─────────────────────────────────────────────────────────────
    %% STAGE 4: AUTOPILOT & DISTRIBUTION
    %% ─────────────────────────────────────────────────────────────
    subgraph S4 ["4. Distribution & Guardrails"]
        direction TB
        BrandSafety["🛡️ Brand Safety Validator\n(Policy & Voice Compliance)"]:::stage4
        LinkedInAuto["🤖 LinkedIn AutoPilot\n(Unipile Scheduler & Comment Triage)"]:::stage4
        BrandSafety --> LinkedInAuto
    end

    %% ─────────────────────────────────────────────────────────────
    %% PERSISTENT STORAGE (SUPABASE)
    %% ─────────────────────────────────────────────────────────────
    subgraph Storage ["💾 Persistent Storage (Supabase)"]
        direction TB
        SupaDB[("PostgreSQL Database\n(Campaigns · Speaker Bios\nPlans · Post Drafts)")]:::storage
        SupaStorage[("Asset Storage\n(9:16 Video MP4s)")]:::storage
    end

    Success(["🚀 Published to LinkedIn\nwith Live Analytics"]):::input

    %% CLEAN HORIZONTAL FLOW (LEFT TO RIGHT)
    UserBrief ==> S1
    S1 ==>|"Live Intelligence"| PlanStart
    HITLReview ==>|"Approved Strategy"| ContextSnapshot
    ContextSnapshot <-->|"Syncs Snapshot"| SupaDB
    ContextSnapshot ==> S3
    MoviePyStitcher -.->|"Uploads MP4"| SupaStorage
    S3 ==>|"Draft Posts & Reels"| S4
    BrandSafety -.->|"Saves Posts"| SupaDB
    LinkedInAuto -.->|"Logs Analytics"| SupaDB
    LinkedInAuto ==> Success
```

---

## 4. Techstack

We prioritize open-source frameworks, local script processing, and free-developer-tier APIs to ensure a **$0 baseline operational cost** for the MVP.

| Layer | Selected Technology | Purpose / Advantage | Cost |
|---|---|---|---|
| **Agent Orchestration** | **LangGraph** (Python) | Graph-based state machine framework supporting cycles (loops) and human interrupts. | **$0** (Open-source) |
| **Relational Database** | **Supabase (PostgreSQL)** | Stores structured event details, schedules, and analytics tracking metrics. | **$0** (Free Tier covers up to 500MB) |
| **Vector Database (RAG)** | **Supabase pgvector** | Stores long-term brand narrative data and tone guides. | **$0** (Included with Supabase instance) |
| **Reasoning & Synthesis** | **Google Gemini 1.5 Flash API** | Drives the strategy brief generation, search snippet parsing, and copy writing. | **$0** (Generous Developer Free Tier) |
| **Search Engine API** | `duckduckgo-search` library | Performs iterative searches to build speaker profiles and retrieve trends. | **$0** (Unlimited, no keys required) |
| **Graphic Generation API** | **Pollinations.ai API** | Generates conceptual background art for templates. | **$0** (No API keys or payment required) |
| **Image manipulation** | **Pillow (PIL) & html2image** | Local Python engine to programmatically overlay speaker photos, brand logos, and titles on templates. | **$0** (Open-source) |
| **Scheduler & Analytics** | **Buffer API** | Standardizes publishing queue and pulls live impressions/clicks data. | **$0** (Free Tier covers 3 channels / 10 posts) |
| **Dashboard Interface** | **Streamlit** (Python) | A simple, fast Python web UI to display dashboards, review panels, and forms. | **$0** (Open-source) |
