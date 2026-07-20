# Research: Session Cache System

**Phase**: 0 — Outline & Research
**Branch**: `003-session-cache-system`
**Date**: 2026-07-14

## Unknowns Resolution

### U1: Concurrency Mechanism

**Decision**: Use `threading.Lock` (reentrant) around all cache mutating operations.

**Rationale**: The constitution mandates "simple dict-based session cache over Redis for V1." Python's built-in `threading.Lock` provides thread-safe access to a shared dict with minimal overhead. A reentrant lock (`RLock`) allows internal helper methods to call each other without deadlock.

**Alternatives considered**:
- `threading.RLock` (chosen) — allows nested lock acquisition within the same thread, safer for composed operations
- `queue.Queue` — unnecessary indirection for dict-based cache
- External Redis — explicitly rejected by constitution (KISS/DRY, no Redis for V1)

### U2: Session ID Generation

**Decision**: Use `uuid.uuid4()` for session identifiers.

**Rationale**: UUID4 provides 122 bits of random entropy, making collisions negligible (1 in 2^71 with 10^18 sessions). No external dependency. Meets FR-07-01 requirement for "sufficient entropy."

**Alternatives considered**:
- `secrets.token_hex(16)` — equivalent security, but UUID4 is more conventional for session IDs
- Auto-incrementing integers — violates "unguessable" session identifier intent from spec
- `uuid.uuid1()` — leaks MAC address and timestamp, unnecessary

### U3: Cleanup Strategy

**Decision**: Lazy expiration on every access operation + periodic sweep via `clear_expired()`.

**Rationale**: Every get/set/delete operation checks the session's last-activity timestamp against current time. Sessions past TTL are treated as expired (not returned) and cleaned on next `clear_expired()` call. This avoids a background thread for V1 while still preventing stale data from being served.

**Alternatives considered**:
- Background thread with daemon timer — adds complexity, over-engineering for V1
- Only lazy expiration — expired sessions consume memory until manual clear
- Lazy + periodic sweep (chosen) — balances memory cleanup with simplicity

### U4: TTL Configuration

**Decision**: TTL as a constructor parameter defaulting to 86400 seconds (24 hours).

**Rationale**: Meets FR-07-12. Constructor injection allows tests to use short TTLs (e.g., milliseconds) without waiting 24 hours. Also allows configuration via environment variable at service level.

**Alternatives considered**:
- Module-level constant — less testable
- Environment variable at cache level — coupling config to the cache class
- Constructor parameter (chosen) — cleanest for testability

## Dependency Analysis

### Internal Dependencies
- `backend/src/config/` — may provide default TTL value from env vars
- `backend/src/agents/` — consumer of session cache (future)

### External Dependencies
None. Standard library only.

### Integration Patterns
- Cache is consumed as a Python class instance (not API endpoints) — created at application startup and injected where needed
- No REST endpoints required for V1 — session cache is internal to the backend
