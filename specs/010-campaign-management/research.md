# Research: Campaign Management Module

## Research 1: Supabase Python SDK Async Patterns

**Decision**: Use Supabase Python SDK with `asyncpg` via the official `supabase` client, leveraging its async methods for FastAPI integration.

**Rationale**: 
- The Supabase Python SDK supports async operations via `create_client` with async methods
- FastAPI is async-native; using async DB calls prevents blocking the event loop
- The existing codebase (feature 009) uses Supabase SDK with async patterns
- Supabase client wraps `postgrest` which has good async support

**Alternatives Considered**:
- Direct `asyncpg` connection pool — More control but loses Supabase features (RLS, auth helpers, realtime)
- SQLAlchemy async with Supabase — Adds ORM overhead; Supabase SDK is lighter for this use case
- Synchronous Supabase SDK in thread pool — Blocks event loop; anti-pattern in FastAPI

**Implementation Pattern**:
```python
from supabase import create_async_client

supabase = create_async_client(url, key)
# Async operations
result = await supabase.table("campaigns").insert(data).execute()
```

---

## Research 2: Optimistic Locking Implementation

**Decision**: Use integer `version` column on `campaigns` table with `WHERE version = expected_version` on UPDATE.

**Rationale**:
- Simple, proven pattern; works with Supabase/PostgreSQL
- `version` increments on each successful update
- UPDATE returns row count; 0 rows = conflict → 409 Conflict
- No additional infrastructure (Redis, etc.) needed
- Compatible with Supabase RLS policies

**Alternatives Considered**:
- Timestamp-based (`updated_at`) — Race conditions if updates happen in same second
- ETag/If-Match header with full row hash — More complex, larger payloads
- PostgreSQL advisory locks — Overkill for this scale; pessimistic locking

**Schema Addition**:
```sql
ALTER TABLE campaigns ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
-- On UPDATE: SET version = version + 1 WHERE id = ? AND version = ?
```

---

## Research 3: Append-Only History Table Design

**Decision**: Application-level append-only enforcement with PostgreSQL triggers as defense-in-depth.

**Rationale**:
- Application layer validates: no DELETE/UPDATE on `campaign_history`
- PostgreSQL trigger prevents direct SQL mutations (safety net)
- Row Level Security (RLS) policies can enforce insert-only for service roles
- Simpler than temporal tables or event sourcing frameworks

**Alternatives Considered**:
- PostgreSQL `SYSTEM VERSIONING` (temporal tables) — Requires PostgreSQL 15+; Supabase may not have it enabled; less flexible for custom event schema
- Event store library (EventStoreDB, etc.) — External dependency; overkill
- Application-only enforcement — Risk if direct DB access bypasses app

**Implementation**:
```sql
-- Table
CREATE TABLE campaign_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id UUID NOT NULL,
    from_state VARCHAR(20),
    to_state VARCHAR(20),
    changed_fields JSONB,
    snapshot JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger to block UPDATE/DELETE
CREATE OR REPLACE FUNCTION prevent_history_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'campaign_history is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER history_immutable
BEFORE UPDATE OR DELETE ON campaign_history
FOR EACH ROW EXECUTE FUNCTION prevent_history_mutation();

-- Index for query performance
CREATE INDEX idx_campaign_history_campaign_id ON campaign_history(campaign_id);
CREATE INDEX idx_campaign_history_timestamp ON campaign_history(timestamp DESC);
```

---

## Research 4: State Machine — Library vs Custom

**Decision**: Custom deterministic state machine (no external library).

**Rationale**:
- Only 6 states and ~10 transitions; custom implementation is <100 lines
- Constitution Principle III (KISS): Avoid unnecessary dependencies
- Constitution Principle V (Linear Pipeline): No LangGraph or workflow engines
- Full control over validation logic, error messages, transition metadata
- Easy to test exhaustively with unit tests
- Zero runtime dependency risk

**Alternatives Considered**:
- `transitions` library — Popular but adds dependency; more complex API than needed
- `statemachine` library — Similar concerns
- LangGraph — Explicitly prohibited by constitution for V1

**Custom Implementation**:
```python
# state_machine.py
VALID_TRANSITIONS = {
    "Draft": ["Ready", "Archived"],
    "Ready": ["Review", "Draft", "Archived"],
    "Review": ["Approved", "Ready", "Archived"],
    "Approved": ["Published", "Review", "Archived"],
    "Published": ["Archived"],
    "Archived": ["Draft", "Ready", "Review", "Approved", "Published"],  # restore to previous
}

def validate_transition(from_state: str, to_state: str) -> tuple[bool, str]:
    if to_state not in VALID_TRANSITIONS.get(from_state, []):
        valid = VALID_TRANSITIONS.get(from_state, [])
        return False, f"Invalid transition from {from_state}. Valid: {valid}"
    return True, ""
```

---

## Research 5: Campaign Asset Storage — Supabase Storage vs Database

**Decision**: Store asset metadata in PostgreSQL (`campaign_assets` table); large binaries (images) in Supabase Storage; small text assets (copy, hashtags) in database JSONB.

**Rationale**:
- Images: Supabase Storage provides CDN, signed URLs, resumable uploads, transformation
- Text assets (copy, hashtags, metadata): Small enough for JSONB; simpler queries, transactions
- Single source of truth for asset references via `campaign_assets` table
- `asset_type` enum distinguishes storage strategy

**Alternatives Considered**:
- All assets in database (BYTEA) — Bloats DB, no CDN, poor performance for images
- All assets in Storage — Overhead for small text; no relational queries
- External S3 — Supabase Storage is already configured and integrated

**Schema**:
```sql
CREATE TABLE campaign_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    asset_type VARCHAR(30) NOT NULL,  -- 'copy', 'image', 'hashtag_set', 'metadata', 'other'
    content JSONB,                     -- For text: {text, format}; for images: {url, width, height, mime}
    storage_path TEXT,                 -- For images: Supabase Storage path
    source VARCHAR(20) NOT NULL,       -- 'ai', 'manual', 'imported'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## Summary of Decisions

| Area | Decision |
|------|----------|
| DB Access | Supabase Python SDK async |
| Concurrency | Integer version column + WHERE version = ? |
| History | Application + trigger enforcement; trigger as safety net |
| State Machine | Custom implementation (no library) |
| Asset Storage | Hybrid: metadata in PG, images in Supabase Storage |

All NEEDS CLARIFICATION items resolved. Ready for Phase 1.