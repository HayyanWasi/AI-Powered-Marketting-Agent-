# Company API Contracts

## Base URL

`/api/company`

## Endpoints

### POST /api/company

Create a new company profile.

**Request Body**:
```json
{
  "name": "Acme Corp",
  "tone": "Professional and innovative"
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "name": "Acme Corp",
  "tone": "Professional and innovative",
  "reference_image_urls": [],
  "created_at": "2026-07-13T00:00:00Z",
  "updated_at": "2026-07-13T00:00:00Z"
}
```

**Errors**:
- 409 Conflict: Company name already exists
- 422 Validation: Missing or invalid fields

---

### GET /api/company/{id}

Get a company profile by ID.

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Acme Corp",
  "tone": "Professional and innovative",
  "reference_image_urls": ["https://...", "https://..."],
  "created_at": "2026-07-13T00:00:00Z",
  "updated_at": "2026-07-13T00:00:00Z"
}
```

**Errors**:
- 404 Not Found: Profile does not exist

---

### PUT /api/company/{id}

Update a company profile.

**Request Body** (partial update):
```json
{
  "name": "Acme Corp Updated",
  "tone": "Modern and bold"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Acme Corp Updated",
  "tone": "Modern and bold",
  "reference_image_urls": ["https://..."],
  "created_at": "2026-07-13T00:00:00Z",
  "updated_at": "2026-07-13T00:00:00Z"
}
```

**Errors**:
- 404 Not Found: Profile does not exist
- 422 Validation: Invalid field values

---

### DELETE /api/company/{id}

Delete a company profile. Does NOT delete associated storage images.

**Response** (204 No Content)

**Errors**:
- 404 Not Found: Profile does not exist

---

### POST /api/company/{id}/brand-images

Upload brand reference images. Accepts multipart/form-data with up to 6 files.

**Request**: multipart/form-data
- Field: `images` (repeated, max 6 files)
- Each file: JPEG, PNG, or WebP, max 10MB

**Response** (200 OK):
```json
{
  "urls": ["https://...", "https://..."],
  "failed": []
}
```

**Errors**:
- 400 Bad Request: File too large, invalid format, more than 6 files
- 404 Not Found: Company profile does not exist
