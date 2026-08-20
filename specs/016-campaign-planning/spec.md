# Spec 016 — Campaign Planning: Specialist Panel + Iterative Refinement

## Problem

A marketer types a campaign goal and currently receives only a single image + caption + hashtags. There is no strategic plan, no audience analysis, no channel strategy, and no approval gate before generation runs.

This leaves professional marketing teams unable to use the tool meaningfully: they cannot review, refine, or confidently sign off on a campaign before expensive generation runs.

## Goal

Transform the app into a professional AI marketing firm:

1. A **panel of 5 specialist agents** (Audience Research, Positioning, Channel Planner, Measurement, Competitive) drafts a full marketing plan in parallel.
2. A **Chief Strategist** synthesises the panel into one coherent plan.
3. The marketer **reviews and refines** the plan section-by-section through a chat interface.
4. The marketer **explicitly approves** the plan — this approval gates content and image generation.
5. Content prompts are **enriched** with USP, messaging pillars, phase, tone, and CTAs from the approved plan.

## Decisions

- Panel of 5 runs concurrently, capped at 3 for Groq free-tier rate limits.
- Plan always covers 4 sections: `core_strategy`, `channel_plan`, `measurement`, `competitive`.
- New page `/dashboard/new-campaign/plan` — plan left, chat right, APPROVE gates `/generate`.
- Agent mirrors user's language in chat prose; plan headings + marketing terms stay English.
- Competitive + AudienceResearch use DuckDuckGo search (not cold-LLM hallucination).
- Refinement state is durable Postgres (not MemorySaver which dies on restart).
- Only named sections regenerate on a critique — untouched sections are byte-identical.

## Database Schema

Migration: `006_create_campaign_plan_tables.up.sql`

### `campaign_plans`
One row per campaign. Tracks lifecycle status and current version pointer.

### `campaign_plan_versions`
Append-only version ledger. Full plan document stored as JSONB.

### `campaign_plan_messages`
Refinement conversation thread. Each marketer message + agent reply is one row.

## API Endpoints

All under `/api/v1/campaigns/{id}/plan/`:

| Method | Path | Description |
|--------|------|-------------|
| POST | `.../plan/draft` | Run the panel graph, store v1 |
| GET | `.../plan` | Return current plan document |
| GET | `.../plan/versions` | Version history |
| GET | `.../plan/versions/{v}` | Specific version |
| GET | `.../plan/messages` | Conversation thread |
| POST | `.../plan/messages` | Submit critique, trigger refinement |
| POST | `.../plan/approve` | Approve plan, unlock generation |

## Verification

```
# Backend
cd backend && pytest

# End-to-end
POST /campaigns/{id}/plan/draft   # 4 sections populated
POST /campaigns/{id}/plan/messages  { "content": "calendar mein aur slots chahiye" }
# → only channel_plan section changed, reply in Roman Urdu
POST /campaigns/{id}/plan/approve
# run generation → USP string present in content prompt
```
