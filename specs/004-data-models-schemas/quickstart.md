# Quickstart: Data Models & Schemas

**Branch**: `004-data-models-schemas`
**Date**: 2026-07-14

## Setup

No additional dependencies. Pydantic already in project. Dataclasses are stdlib.

## Usage

```python
from src.models.guest import Guest, GuestCreate, GuestResponse

# Create via Pydantic schema (API validation layer)
guest_data = GuestCreate(name="Jane Doe", title="Speaker", company="Acme Inc", bio="Expert in AI")
guest_dict = guest_data.model_dump()
# {"name": "Jane Doe", "title": "Speaker", "company": "Acme Inc", "bio": "Expert in AI"}

# Create internal dataclass
guest = Guest(name="Jane Doe", title="Speaker")
guest.name  # "Jane Doe"

# Serialize to response
response = GuestResponse(id=str(uuid4()), name=guest.name, ...)
response.model_dump_json()
```

## Test Expectations

| Area | Description |
|------|-------------|
| Guest validation | Required fields reject empty; optional fields accept omission |
| Campaign validation | Type/caption required; status must be valid value |
| Serialization | Dataclass ↔ Pydantic round-trip with zero data loss |
| URL validation | Invalid URLs flagged; valid URLs accepted |
| Company compatibility | Existing models unchanged, new models follow same pattern |
