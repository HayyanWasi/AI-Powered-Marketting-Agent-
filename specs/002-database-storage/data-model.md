# Data Model: Database & Storage Setup

## Entity: CompanyProfile

Represents a single marketing organization with brand identity and reference images for campaign generation.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, default `gen_random_uuid()` | Unique company identifier |
| `name` | TEXT | NOT NULL, unique | Company/organization name |
| `tone` | TEXT | NOT NULL | Brand voice/tone description |
| `reference_image_urls` | TEXT[] | NOT NULL, default `'{}'`, max 6 | Public URLs of brand reference images |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default `NOW()` | Last update timestamp |

### Validation Rules

- `name`: Must be non-empty, trimmed, max 255 characters
- `tone`: Must be non-empty, trimmed, max 1000 characters
- `reference_image_urls`: Max 6 URLs, each URL max 2048 characters
- Duplicate `name` rejected (single-company V1 mode)

### State Transitions

- **Create**: Profile with `name`, `tone`, optional initial images
- **Read**: Profile fetched by `id`
- **Update**: `name`, `tone`, `reference_image_urls` can be modified; `updated_at` auto-refreshes
- **Delete**: Profile removed; associated storage images NOT deleted

### Business Rules

- V1 supports only one company profile at a time
- Creating a new profile when one exists is blocked
- Brand reference images are uploaded independently and linked by URL

## Entity: BrandReferenceImage

Represents an image file stored in Supabase Storage.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `file` | Uploaded file | Image file (multipart/form-data) |
| `storage_path` | TEXT | Path in Supabase Storage bucket |
| `public_url` | TEXT | Permanent public URL after upload |

### Validation Rules

- File size <= 10MB
- File must be a valid image (JPEG, PNG, WebP)
- At least 1080x1080 resolution (per constitution quality gates)
