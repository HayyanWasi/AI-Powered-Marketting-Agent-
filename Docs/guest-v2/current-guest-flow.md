# Current Guest Flow Audit (V1)

## Architecture Overview

**Current entry point:**
- `backend/src/api/routes/guest.py` and `backend/src/api/v1/guest.py`

**Current search implementation:**
- `backend/src/services/search.py` (`GuestSearchService` using DuckDuckGo/DDGS)
- `backend/src/modules/workflow_engine/graphs/guest_research.py` (LangGraph workflow for orchestrating research)
- `backend/src/agents/context_builder.py` (`_summarize_search` function)

**Current guest model:**
- `backend/src/models/guest.py` (`Guest`, `GuestCreate`, `GuestUpdate`, `GuestResponse` - representing the campaign relationship/entity)
- `backend/src/models/guest_profile.py` (`GuestProfile`, `GuestProfileData`, `GuestSearchRequest`)
- `backend/src/agents/context.py` (`GuestData` with `biography` field)

**Current repository:**
- Database logic is likely co-located with `Guest` entity in `backend/src/models/guest.py` or `backend/src/repositories/guest.py` (requires further inspection during refactoring).

**Current API:**
- Legacy (`v1`) and active (`routes`) endpoints that expose search and synthesis directly.

**Current LLM usage:**
- `backend/src/services/llm.py` and `backend/src/config/prompts.py` define structures containing `professional_biography`.

**Current biography storage:**
- Stored directly on `GuestData.biography` or `GuestProfile.professional_biography`. 

**Current content-generation usage:**
- `backend/src/agents/content_generator.py` (Lines 191-193) directly injects the raw biography into the prompt loop: `f"- {g.full_name} ({getattr(g, 'position', '')}): {g.biography}"`.
- `backend/src/modules/linkedin/generators/post_generator.py` injects `professional_biography` into the post generation prompt.

## File Disposition Plan

### Files that can be removed (Old Research Implementation)
- `backend/src/services/search.py` (The DDG-based search service)
- `backend/src/modules/workflow_engine/graphs/guest_research.py` (If fully replaced by the new deterministic `GuestProfileService`)
- Any `DuckDuckGo` dependencies in `pyproject.toml`.

### Files that must remain (Campaign Relationship)
- `backend/src/models/guest.py` (The campaign guest linkage must persist).
- Campaign APIs and database migrations preserving the `campaign_guests` tables.

### Files that require modification
- **Generators:** `backend/src/agents/content_generator.py` and `backend/src/modules/linkedin/generators/post_generator.py` (Must stop injecting raw biography; instead use deterministic `ContextSelector`).
- **Context Builder:** `backend/src/agents/context_builder.py` and `backend/src/agents/context.py` (Swap raw `biography` string for structured `GuestContext`).
- **API Routes:** `backend/src/api/routes/guest.py` and `backend/src/api/v1/guest.py` (Migrate to the new `GuestProfileService` and structured data logic).
- **Models:** `backend/src/models/guest_profile.py` (Restructure to match the new `GuestProfile` and `GuestEvidence` schema).
- **Prompts:** `backend/src/config/prompts.py` (Enforce structured JSON output without fabricating facts).
