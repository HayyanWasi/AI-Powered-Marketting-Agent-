# Session Cache Interface Contract

**Branch**: `003-session-cache-system`
**Date**: 2026-07-14

## Overview

Public API of the `SessionCache` class. This is an internal Python interface (not HTTP/REST). All methods are thread-safe.

## Constructor

### `SessionCache(ttl: float = 86400)`

Creates a new cache instance with the given TTL in seconds.

- `ttl` — seconds of inactivity before a session expires (default: 86400 = 24h)
- Raises: `ValueError` if `ttl <= 0`

## Methods

### `create_session() -> str`

Creates a new guest session.

- Returns: unique session ID (UUID4 string)
- Side effects: session stored in cache with current timestamp

### `get_session(session_id: str) -> Session | None`

Retrieves a session by ID without modifying last_activity.

- Returns: `Session` if found and not expired; `None` otherwise
- Refreshes last_activity timestamp (per FR-07-05)

### `session_exists(session_id: str) -> bool`

Checks if a non-expired session exists.

- Returns: `True` if session exists and not expired; `False` otherwise
- Does NOT refresh last_activity

### `store_data(session_id: str, key: str, value: Any) -> bool`

Stores a value under the given key within a session.

- Returns: `True` if successful; `False` if session not found or expired
- Refreshes last_activity
- Raises: `ValueError` if `key` is empty or not a string

### `get_data(session_id: str, key: str) -> tuple[Any, bool]`

Retrieves the value for a given key within a session.

- Returns: `(value, True)` if found; `(None, False)` if key or session not found
- Refreshes last_activity if session found
- Expired sessions return `(None, False)`

### `update_data(session_id: str, key: str, value: Any) -> bool`

Updates existing data or creates new key-value entry within a session.

- Returns: `True` if successful; `False` if session not found or expired
- Refreshes last_activity
- Same semantics as `store_data` for the caller

### `delete_data(session_id: str, key: str) -> bool`

Removes a key-value entry from a session.

- Returns: `True` if key existed and was removed; `False` if key or session not found
- Refreshes last_activity if session found

### `delete_session(session_id: str) -> bool`

Removes an entire session from the cache.

- Returns: `True` if session existed and was removed; `False` if not found
- Does NOT error if session is already expired

### `clear_all() -> None`

Removes all sessions from the cache (both active and expired).

- Always succeeds. No-op on empty cache.

### `clear_expired() -> int`

Removes all expired sessions from the cache.

- Returns: count of sessions removed
- Active (non-expired) sessions are preserved

## Error Handling

All methods handle internal errors gracefully:

- **Lock acquisition failure**: Methods will block on the reentrant lock; no timeout in V1
- **Invalid input types**: `TypeError` may propagate for clearly wrong types (e.g., non-string session_id)
- **Empty cache**: `clear_all()` and `clear_expired()` no-op on empty state
- **Non-existent session**: Return `False` or `None` — no exception raised

## Thread Safety

- All public methods acquire `self._lock` (RLock) before mutating state
- Read operations acquire the lock to ensure consistent view
- Lock is released on method exit (via `with` statement)
