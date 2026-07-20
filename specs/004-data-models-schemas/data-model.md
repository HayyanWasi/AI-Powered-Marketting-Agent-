# Data Model: Data Models & Schemas

**Branch**: `004-data-models-schemas`
**Date**: 2026-07-14

## Entities

### Guest

Represents an event speaker or guest whose profile is used in campaign content generation.

**Fields (Dataclass):**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Full name of the guest |
| `title` | string | No | `""` | Professional title/position |
| `company` | string | No | `""` | Organization name |
| `bio` | string | No | `""` | Short biographical text |

**Pydantic Schemas:**
- `GuestCreate` — name (required, 1-255 chars), title/company/bio (optional, max 1000 chars each)
- `GuestUpdate` — all fields optional with same constraints
- `GuestResponse` — all fields including id and timestamps

**Validation Rules:**
- `name`: Non-empty, non-whitespace string, max 255 characters
- `title`, `company`, `bio`: Optional, max 1000 characters when provided

### Campaign

Represents a single generated social media campaign output.

**Fields (Dataclass):**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | Yes | — | Campaign type identifier (e.g., speaker promo, event recap) |
| `caption` | string | Yes | — | Generated caption text |
| `image_url` | string | No | `""` | URL to generated campaign image |
| `status` | string | Yes | `"draft"` | Lifecycle state |

**Pydantic Schemas:**
- `CampaignCreate` — type/caption (required), image_url/status (optional with defaults)
- `CampaignUpdate` — all fields optional
- `CampaignResponse` — all fields including id and timestamps

**Validation Rules:**
- `type`: Non-empty string, must match known campaign type
- `caption`: Non-empty, non-whitespace string, platform-dependent character limits enforced at service layer
- `image_url`: Valid HTTP/HTTPS URL when provided
- `status`: One of `draft`, `published`, `archived`

### Company

Represents a marketing organization's brand identity. **Already implemented** in `backend/src/models/company.py`.

**Fields (Dataclass):**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string (UUID) | Yes | Auto-generated | Unique identifier |
| `name` | string | Yes | — | Company name |
| `tone` | string | Yes | — | Brand tone description |
| `reference_image_urls` | list[string] | No | `[]` | Up to 6 brand reference image URLs |

## Entity Relationships

```
Company (1)
  └── has * ─── Campaign (*)
                   └── references 0..1 ─── Guest (optional)
```

- A Company can have many Campaigns
- A Campaign may reference a Guest (optional, for speaker-focused campaigns)
- Guest has no mandatory relationships — reusable profile data

## State Transitions

### Campaign Status

```
draft ──→ published
draft ──→ archived
published ──→ archived
```

- `draft`: Initial state, editable
- `published`: Finalized and displayed, no further edits
- `archived`: Hidden from active views but preserved
