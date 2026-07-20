# Data Model: Session Cache System

**Branch**: `003-session-cache-system`
**Date**: 2026-07-14

## Entities

### Session

Represents a single guest user's ephemeral data container with automatic expiry.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string (UUID4) | Yes | Unique identifier, auto-generated on creation |
| `data` | dict (string → any) | Yes | Arbitrary key-value payload for the session |
| `created_at` | float (unix timestamp) | Yes | When the session was first created |
| `last_activity` | float (unix timestamp) | Yes | When the session was last read or written; used for TTL expiry |

**Validation Rules:**
- `session_id`: Must be a valid UUID4 string; auto-generated — not user-supplied
- `data`: Keys must be non-empty strings; values must be JSON-serializable
- `created_at` and `last_activity`: Set automatically by the system, not user-supplied
- `last_activity` MUST be >= `created_at` at all times
- Expiry check: `current_time - last_activity > TTL` → session is expired

**State Transitions:**
```
Created → Active (read/write operations) → Expired (timeout)
                                              ↓
                                         Removed (clear_expired / clear_all)
```

### SessionCache

The container managing all active sessions.

| Field | Type | Description |
|-------|------|-------------|
| `sessions` | dict (string → Session) | Map of session_id to Session objects |
| `ttl` | float | Time-to-live in seconds (default 86400 = 24 hours) |
| `lock` | threading.RLock | Reentrant lock for thread-safe access |

## Relationship Diagram

```
SessionCache (1)
  └── manages * ─── Session (*)
                      └── contains * ─── Key-Value entry (string → any)
```

## Validation Rules Summary

| Rule | Source FR | Description |
|------|-----------|-------------|
| Unique session ID | FR-07-01 | No two sessions share the same ID |
| Max TTL inactivity | FR-07-06 | Session expires after TTL seconds of inactivity |
| Activity tracking | FR-07-05 | Every read/write refreshes last_activity |
| Expired data blocked | FR-07-07 | Expired sessions return "not found" |
| Empty cache clear | FR-07-09 | Clear on empty cache succeeds without error |
| Expired-only clear | FR-07-10 | Only expired sessions removed; active preserved |
| Configurable TTL | FR-07-12 | TTL default 86400s, overridable at construction |
