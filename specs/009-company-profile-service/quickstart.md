# Quickstart: Company Profile Service

## Overview

The Company Profile Service provides REST endpoints to create, retrieve, update, and manage company brand profiles. Each profile stores brand guidelines and up to six reference images used by Campaign Generation to produce on-brand content.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/company-profiles` | Create a new profile |
| GET | `/api/v1/company-profiles` | List all profiles |
| GET | `/api/v1/company-profiles/{profile_id}` | Get profile by ID |
| PUT | `/api/v1/company-profiles/{profile_id}` | Update profile |
| POST | `/api/v1/company-profiles/{profile_id}/images` | Upload brand image |
| GET | `/api/v1/company-profiles/{profile_id}/images` | List profile images |
| DELETE | `/api/v1/company-profiles/{profile_id}/images/{image_id}` | Remove image |
| PUT | `/api/v1/company-profiles/{profile_id}/images/{image_id}/reorder` | Reorder image |

## Quick Start Examples

### Create a Company Profile

```bash
curl -X POST http://localhost:8000/api/v1/company-profiles \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme Corp",
    "brand_guidelines": "Use professional, confident language. Primary color: blue #0055FF. Avoid jargon.",
    "brand_tone": "Professional and innovative"
  }'
```

Response: `201 Created`
```json
{
  "id": "a1b2c3d4-...",
  "company_name": "Acme Corp",
  "brand_guidelines": "Use professional, confident language...",
  "brand_tone": "Professional and innovative",
  "reference_images": [],
  "created_at": "2026-07-15T12:00:00Z",
  "updated_at": "2026-07-15T12:00:00Z"
}
```

### Upload a Brand Image

```bash
curl -X POST http://localhost:8000/api/v1/company-profiles/a1b2c3d4-.../images \
  -F "image=@logo.png"
```

Response: `201 Created`
```json
{
  "id": "x1y2z3-...",
  "url": "https://storage.example.com/images/x1y2z3-....png",
  "filename": "logo.png",
  "sort_order": 0,
  "uploaded_at": "2026-07-15T12:01:00Z"
}
```

### Retrieve a Profile (for Campaign Generation)

```bash
curl http://localhost:8000/api/v1/company-profiles/a1b2c3d4-...
```

Returns all brand information including image URLs for use in campaign generation.

## Key Business Rules

- **Minimum requirements**: Company name + brand guidelines must be present before profile can be used for campaign generation.
- **Image limit**: Maximum 6 brand reference images per profile.
- **Uniqueness**: Company names are unique — creating or updating to a duplicate returns `409 Conflict`.
- **Persistence**: Profiles and images persist across user sessions.

## Dependencies

- **Supabase PostgreSQL**: `company_profiles` table for profile records, `brand_reference_images` table for image metadata.
- **Supabase Storage**: Public bucket for storing uploaded brand images.
- **Pillow**: Image validation (resolution >= 1080x1080, format check).
- **FastAPI**: HTTP framework hosting the service endpoints.
