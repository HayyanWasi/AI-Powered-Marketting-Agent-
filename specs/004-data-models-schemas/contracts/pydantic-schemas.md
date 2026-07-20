# Pydantic Schema Contracts

**Branch**: `004-data-models-schemas`
**Date**: 2026-07-14

## Overview

Pydantic BaseModel schemas for API request/response validation. Each entity has three schemas: Create, Update, and Response, following the existing `company.py` pattern.

## Guest Schemas

### `GuestCreate`

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | `str` | Yes | 1-255 chars, non-empty |
| `title` | `str \| None` | No | Max 1000 chars |
| `company` | `str \| None` | No | Max 1000 chars |
| `bio` | `str \| None` | No | Max 1000 chars |

### `GuestUpdate`

All fields optional, same constraints as GuestCreate.

### `GuestResponse`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier (UUID) |
| `name` | `str` | Full name |
| `title` | `str` | Professional title |
| `company` | `str` | Organization |
| `bio` | `str` | Biography |
| `created_at` | `str` | ISO 8601 timestamp |
| `updated_at` | `str` | ISO 8601 timestamp |

### `Guest` (dataclass)

Internal representation mirroring GuestResponse fields. Used by services.

## Campaign Schemas

### `CampaignCreate`

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Non-empty, recognized campaign type |
| `caption` | `str` | Yes | Non-empty, non-whitespace |
| `image_url` | `str \| None` | No | Valid HTTP(S) URL |
| `status` | `str` | No | Default: `"draft"`, one of: draft, published, archived |

### `CampaignUpdate`

All fields optional, same constraints as CampaignCreate.

### `CampaignResponse`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier (UUID) |
| `type` | `str` | Campaign type |
| `caption` | `str` | Generated caption |
| `image_url` | `str \| None` | Image URL |
| `status` | `str` | Lifecycle state |
| `created_at` | `str` | ISO 8601 timestamp |
| `updated_at` | `str` | ISO 8601 timestamp |

### `Campaign` (dataclass)

Internal representation mirroring CampaignResponse fields. Used by services.

## Company Schemas

Already implemented in `backend/src/models/company.py`:

- `CompanyProfileCreate` — name (required), tone (required)
- `CompanyProfileUpdate` — name (optional), tone (optional)
- `CompanyProfileResponse` — id, name, tone, reference_image_urls, created_at, updated_at
- `CompanyProfile` (dataclass) — internal representation with `to_response()` method

## Common Validation Rules

- **String fields**: Stripped of leading/trailing whitespace before validation
- **URL fields**: Must start with `http://` or `https://`
- **ID fields**: Auto-generated UUID v4 strings
- **Timestamp fields**: ISO 8601 format strings, auto-generated on creation
