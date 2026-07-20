# Quickstart: Campaign Management Module

## Overview

The Campaign Management module provides a REST API for managing marketing campaign lifecycles. This guide covers the essential operations to create, configure, transition, and publish campaigns.

## Base URL

```
http://localhost:8000/api/v1
```

All endpoints require authentication via Bearer token (JWT).

---

## 1. Create a Campaign

Create a new campaign in `Draft` state.

```bash
curl -X POST http://localhost:8000/api/v1/campaigns \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q4 Holiday Sale 2026",
    "goals": {
      "primary": "Drive holiday sales",
      "metrics": ["revenue", "conversion_rate"],
      "targets": {"revenue": 50000, "conversion_rate": 0.03}
    },
    "target_audience": {
      "segments": ["existing_customers", "high_value"],
      "demographics": {"age_range": "25-45", "location": "US"},
      "interests": ["holiday shopping", "deals"]
    },
    "platforms": ["instagram", "facebook", "linkedin"],
    "schedule": {
      "start_date": "2026-11-15T09:00:00Z",
      "end_date": "2026-12-31T23:59:59Z",
      "timezone": "America/New_York"
    },
    "metadata": {"campaign_type": "seasonal", "budget": 10000}
  }'
```

**Response (201 Created):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "organization_id": "org-uuid",
  "company_profile_id": null,
  "name": "Q4 Holiday Sale 2026",
  "goals": {...},
  "target_audience": {...},
  "platforms": ["instagram", "facebook", "linkedin"],
  "schedule": {...},
  "metadata": {...},
  "state": "Draft",
  "version": 1,
  "created_at": "2026-07-16T10:00:00Z",
  "updated_at": "2026-07-16T10:00:00Z",
  "published_at": null,
  "archived_at": null,
  "created_by": "user-uuid",
  "updated_by": "user-uuid"
}
```

---

## 2. Update Campaign Configuration (Draft Only)

Modify campaign details while in `Draft` state. Use `If-Match` header for optimistic locking.

```bash
curl -X PUT http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "If-Match: 1" \
  -d '{
    "goals": {
      "primary": "Drive holiday sales with email capture",
      "metrics": ["revenue", "conversion_rate", "email_signups"],
      "targets": {"revenue": 50000, "conversion_rate": 0.03, "email_signups": 5000}
    }
  }'
```

**Response (200 OK):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "version": 2,
  "goals": {...},
  "updated_at": "2026-07-16T10:05:00Z",
  "state": "Draft"
}
```

---

## 3. Advance Campaign Through Lifecycle

### Draft → Ready
```bash
curl -X POST http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890/transition \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to_state": "Ready", "reason": "Configuration complete"}'
```

### Ready → Review
```bash
curl -X POST http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890/transition \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to_state": "Review", "reason": "Ready for team review"}'
```

### Review → Approved (requires approver role)
```bash
curl -X POST http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890/transition \
  -H "Authorization: Bearer APPROVER_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to_state": "Approved", "reason": "Approved by marketing lead"}'
```

### Approved → Published
```bash
curl -X POST http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890/transition \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to_state": "Published", "reason": "Go live"}'
```

**Response (200 OK):**
```json
{
  "campaign": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "state": "Published",
    "version": 5,
    "published_at": "2026-07-16T11:00:00Z",
    ...
  },
  "history_entry": {
    "id": "hist-uuid",
    "event_type": "StateTransitioned",
    "from_state": "Approved",
    "to_state": "Published",
    "timestamp": "2026-07-16T11:00:00Z",
    "actor_id": "user-uuid"
  }
}
```

---

## 4. Archive and Restore

### Archive a Published Campaign
```bash
curl -X POST http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890/archive \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Campaign concluded"}'
```

### Restore Archived Campaign
```bash
curl -X POST http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890/restore \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
Restores to the state before archiving (e.g., `Published`).

---

## 5. Retrieve Campaign with Assets

```bash
curl -X GET http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 6. View Campaign History

```bash
curl -X GET "http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890/history?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "history": [
    {
      "id": "hist-uuid-3",
      "event_type": "StateTransitioned",
      "timestamp": "2026-07-16T11:00:00Z",
      "actor_id": "user-uuid",
      "from_state": "Approved",
      "to_state": "Published",
      "changed_fields": null,
      "snapshot": {...},
      "metadata": {"reason": "Go live"}
    },
    {
      "id": "hist-uuid-2",
      "event_type": "StateTransitioned",
      "timestamp": "2026-07-16T10:30:00Z",
      "actor_id": "approver-uuid",
      "from_state": "Review",
      "to_state": "Approved",
      "changed_fields": null,
      "snapshot": {...},
      "metadata": {"reason": "Approved by marketing lead"}
    },
    {
      "id": "hist-uuid-1",
      "event_type": "Created",
      "timestamp": "2026-07-16T10:00:00Z",
      "actor_id": "user-uuid",
      "from_state": null,
      "to_state": "Draft",
      "changed_fields": null,
      "snapshot": {...},
      "metadata": {}
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 20
}
```

---

## 7. Manage Campaign Assets

### Add Copy Asset
```bash
curl -X POST http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890/assets \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_type": "copy",
    "content": {
      "asset_type": "copy",
      "text": "🎄 Holiday Sale is LIVE! Up to 50% off everything. Shop now! #HolidaySale #Deals",
      "format": "markdown"
    },
    "source": "ai"
  }'
```

### Add Image Asset
```bash
curl -X POST http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890/assets \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_type": "image",
    "content": {
      "asset_type": "image",
      "url": "https://storage.supabase.co/brand-images/campaign-hero.png",
      "width": 1920,
      "height": 1080,
      "mime_type": "image/png"
    },
    "source": "imported",
    "storage_path": "campaigns/a1b2c3d4/hero.png"
  }'
```

### List Assets
```bash
curl -X GET http://localhost:8000/api/v1/campaigns/a1b2c3d4-e5f6-7890-abcd-ef1234567890/assets \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 8. List Campaigns with Filters

```bash
# All active campaigns
curl -X GET "http://localhost:8000/api/v1/campaigns?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Only Published campaigns
curl -X GET "http://localhost:8000/api/v1/campaigns?state=Published" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Date range
curl -X GET "http://localhost:8000/api/v1/campaigns?start_date=2026-07-01&end_date=2026-07-31" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Error Responses

### 400 Validation Error
```json
{
  "detail": "Validation failed",
  "code": "VALIDATION_ERROR",
  "invalid_fields": ["goals.primary", "schedule.start_date"]
}
```

### 409 State Transition Invalid
```json
{
  "detail": "Cannot transition from Draft to Published. Valid next states: Ready, Archived",
  "code": "STATE_TRANSITION_INVALID"
}
```

### 409 Version Conflict
```json
{
  "detail": "Campaign was modified by another user. Expected version 1, found 2",
  "code": "VERSION_CONFLICT"
}
```

### 404 Not Found
```json
{
  "detail": "Campaign not found",
  "code": "NOT_FOUND"
}
```

---

## Key Rules Summary

| Operation | Allowed States | Notes |
|-----------|---------------|-------|
| Create | — | Creates in Draft |
| Update Config | Draft only | Requires If-Match header |
| Transition | Per state graph | Validates preconditions |
| Archive | Any | Moves to Archived |
| Restore | Archived only | Returns to previous state |
| Delete | Draft only | Hard delete |
| Add Assets | Any | No state restriction |
| Read | Any | No restriction |

---

## Next Steps

- Integrate with **Campaign Generation** (reads campaign config + assets)
- Integrate with **Publishing Service** (consumes Published campaigns)
- Add webhook notifications for state transitions
- Implement analytics module (future)