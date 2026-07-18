# Data Model: Company Profile Service

## Entities

### CompanyProfile

Represents a company's brand identity information used for AI-powered campaign generation.

| Field | Type | Required | Unique | Notes |
|-------|------|----------|--------|-------|
| id | UUID | Yes | Yes | System-generated identifier |
| company_name | string | Yes | Yes | Human-readable company name |
| brand_guidelines | string | Yes | No | Brand communication rules and style guide text |
| brand_tone | string | No | No | Optional tone descriptor (e.g., "professional", "playful") |
| reference_images | list[string] | No | No | Ordered list of image identifiers/URLs (max 6) |
| created_at | datetime | Yes | No | Timestamp of profile creation |
| updated_at | datetime | Yes | No | Timestamp of last profile update |

### BrandReferenceImage

A visual asset associated with a company profile.

| Field | Type | Required | Unique | Notes |
|-------|------|----------|--------|-------|
| id | UUID | Yes | Yes | System-generated identifier |
| company_profile_id | UUID | Yes | No | Foreign key to CompanyProfile |
| storage_path | string | Yes | No | Path in blob storage |
| filename | string | Yes | No | Original uploaded filename |
| content_type | string | Yes | No | MIME type (image/jpeg, image/png, image/webp) |
| file_size | integer | Yes | No | Size in bytes |
| sort_order | integer | Yes | No | Position in ordered list (0-5) |
| uploaded_at | datetime | Yes | No | Timestamp of upload |

## Relationships

```
CompanyProfile (1) ────── (0..6) BrandReferenceImage
CompanyProfile (1) ────── (0..N) Campaign (external)
```

- A CompanyProfile has zero to six BrandReferenceImages.
- A CompanyProfile is referenced by many Campaigns (relationship managed by Campaign service).

## Validation Rules

| Rule | Scope | Enforcement Point |
|------|-------|-------------------|
| company_name must be non-empty | Create, Update | API validation |
| company_name must be unique | Create, Update | Database unique constraint |
| brand_guidelines must be non-empty | Create, Update | API validation |
| Max 6 reference images per profile | Image upload | Business logic check before insert |
| Image must be valid JPEG/PNG/WebP | Image upload | File validation on upload |
| Image must be >= 1080x1080 | Image upload | Resolution check (per constitution) |
| Profile is "complete" if company_name AND brand_guidelines are present | Campaign generation | Business rule check |
| Reference images must remain accessible while associated | Throughout | Storage lifecycle management |

## State Transitions

```
[Empty] --(create)--> [Active]
[Active] --(update)--> [Active]
[Active] --(delete)--> [Deleted]
```

- A profile is created in "Active" state with complete or partial data.
- Only "Complete" profiles (name + guidelines present) can be used for campaign generation.
- Incomplete profiles can be updated to become complete.
- Deleted profiles: TBD — soft delete vs hard delete depends on campaign history requirements.
