# Quickstart: Session Cache System

**Branch**: `003-session-cache-system`
**Date**: 2026-07-14

## Setup

No additional dependencies required. Standard library only.

## Usage

```python
from backend.src.cache import SessionCache

# Create cache with 24-hour TTL (default)
cache = SessionCache()

# Create a guest session
session_id = cache.create_session()

# Store data
cache.store_data(session_id, "preferred_language", "en")
cache.store_data(session_id, "draft_content", "Hello world")

# Retrieve data
lang, found = cache.get_data(session_id, "preferred_language")
# lang = "en", found = True

# Update data
cache.update_data(session_id, "preferred_language", "fr")

# Delete individual key
cache.delete_data(session_id, "draft_content")

# Check session exists
cache.session_exists(session_id)  # True

# Delete entire session
cache.delete_session(session_id)

# Clear all sessions
cache.clear_all()

# Clear only expired sessions
removed = cache.clear_expired()
```

## Testing TTL

```python
import time

# Create cache with 1ms TTL for testing
cache = SessionCache(ttl=0.001)
session_id = cache.create_session()
time.sleep(0.002)

cache.session_exists(session_id)  # False (expired)
```

## Test Expectations

See FR-07 and acceptance scenarios in [spec.md](spec.md). Key test areas:

| Area | Description |
|------|-------------|
| Session CRUD | Create, read, update, delete sessions |
| Data CRUD | Store, get, update, delete key-value entries |
| TTL expiry | Session expires after TTL; stale data never returned |
| Activity refresh | Read/write resets expiry timer |
| Concurrent access | 100 ops across 50 sessions without corruption |
| Manual clear | `clear_all()` removes everything; `clear_expired()` removes only expired |
| Edge cases | Empty cache clear, non-existent session, zero TTL |
