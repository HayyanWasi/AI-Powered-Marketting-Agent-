# Data Model: Pollinations AI Brand Image Generation

## Entities

### CompanyProfile
Represents a company's brand identity stored in Supabase `company_profiles` table.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| name | string | Yes | Company name |
| brand_colors | JSON array[string] | No | Hex color codes (e.g., ["#FF6B35", "#004E89"]) |
| brand_personality | string | No | Descriptors (e.g., "modern minimalist", "vintage retro") |
| style_guide | string | No | Text description of visual style |
| logo_url | string | No | URL to logo image (Supabase Storage or external) |
| typography_style | string | No | Font style preferences |
| reference_images | JSON array[string] | No | Array of brand reference image URLs |
| industry_category | string | No | Industry for context |
| created_at | datetime | Yes | Timestamp |
| updated_at | datetime | Yes | Timestamp |

**Validation Rules**:
- `brand_colors`: Array of valid hex codes (3 or 6 digit, with #)
- `logo_url`: Valid HTTPS URL if present
- `reference_images`: Array of valid HTTPS URLs

**Relationships**: 
- One-to-many with CampaignImageRequest (via company_profile_id)

---

### CampaignImageRequest
Request payload for generating a campaign image.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| company_profile_id | UUID | Yes | Reference to CompanyProfile |
| campaign_prompt | string | Yes | Natural language description of campaign image |
| campaign_context | object | No | Additional context (target platform, audience, etc.) |

**Validation Rules**:
- `company_profile_id`: Valid UUID format
- `campaign_prompt`: 10-500 characters, non-empty
- `campaign_context`: Optional JSON object

---

### CampaignImageResponse
Response payload after successful image generation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| image_url | string | Yes | Pollinations CDN URL (https://image.pollinations.ai/...) |
| model | string | Yes | Model used (always "kontext") |
| generation_time_ms | integer | Yes | Total time including retries |
| fallback_used | boolean | Yes | True if fallback was activated |
| brand_conditioning_applied | boolean | Yes | True if brand fields were available and used |

**Example**:
```json
{
  "image_url": "https://image.pollinations.ai/prompt/summer%20sale%20campaign%20brand%20colors%20%23FF6B35%20%23004E89%20modern%20minimalist?model=kontext",
  "model": "kontext",
  "generation_time_ms": 12450,
  "fallback_used": false,
  "brand_conditioning_applied": true
}
```

---

### BrandStyleContext
Derived entity: extracted and formatted brand attributes for prompt conditioning. Not persisted.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| color_palette | string | No | Comma-separated hex codes for prompt |
| personality_descriptors | string | No | Brand personality for prompt |
| style_guidance | string | No | Style guide text for prompt |
| logo_reference | string | No | Logo description/URL for prompt |
| reference_image_urls | array[string] | No | Brand reference images for prompt |

**Derivation Rules**:
- `color_palette`: Join `brand_colors` with ", " (e.g., "#FF6B35, #004E89")
- `personality_descriptors`: Use `brand_personality` directly
- `style_guidance`: Use `style_guide` directly
- `logo_reference`: If `logo_url` present, include "logo style from {logo_url}"
- `reference_image_urls`: Use `reference_images` array directly

---

### PollinationsPrompt
Internal value object: the complete prompt sent to Pollinations API.

| Field | Type | Description |
|-------|------|-------------|
| base_prompt | string | Campaign prompt + brand conditioning |
| model | string | Always "kontext" |
| negative_prompt | string | Optional negative constraints |

**Construction**:
```
base_prompt = f"{campaign_prompt}, {brand_conditioning}"
brand_conditioning = ", ".join(filter(None, [
    f"brand colors {color_palette}" if color_palette else None,
    f"{personality_descriptors} style" if personality_descriptors else None,
    style_guidance if style_guidance else None,
    f"logo reference {logo_reference}" if logo_reference else None
]))
```

---

### ImageValidationResult
Internal value object: result of image validation.

| Field | Type | Description |
|-------|------|-------------|
| is_valid | boolean | Passes all checks |
| width | integer | Image width in pixels |
| height | integer | Image height in pixels |
| content_type | string | MIME type (image/png, image/jpeg, etc.) |
| errors | array[string] | Validation error messages |
| url_accessible | boolean | HEAD request succeeded |

**Validation Rules**:
- `is_valid` = True only if: url_accessible AND width >= 1080 AND height >= 1080 AND content_type starts with "image/"
- Minimum resolution: 1080x1080 (Instagram/LinkedIn compatible)

---

## State Transitions

### CampaignImageRequest Processing Flow

```
REQUEST_RECEIVED
    ↓ (validate request)
VALIDATED
    ↓ (fetch company profile)
PROFILE_LOADED / PROFILE_NOT_FOUND
    ↓ (extract brand context)
BRAND_CONTEXT_READY
    ↓ (build prompt)
PROMPT_BUILT
    ↓ (call Pollinations)
GENERATION_STARTED
    ↓ (on success)
IMAGE_URL_RECEIVED
    ↓ (validate image)
VALIDATION_PASSED / VALIDATION_FAILED
    ↓ (on validation fail, retry once)
RETRY_GENERATION / FALLBACK_GENERATION
    ↓ (on final success)
COMPLETED
    ↓ (on total failure)
FAILED
```

---

## API Error Responses

### 400 Bad Request
```json
{
  "error": "validation_error",
  "message": "Invalid request parameters",
  "details": [
    {"field": "campaign_prompt", "message": "Campaign prompt must be 10-500 characters"}
  ]
}
```

### 404 Not Found
```json
{
  "error": "not_found",
  "message": "Company profile not found",
  "details": {"company_profile_id": "uuid"}
}
```

### 422 Unprocessable Entity
```json
{
  "error": "validation_failed",
  "message": "Generated image does not meet requirements",
  "details": {
    "width": 800,
    "height": 600,
    "minimum": "1080x1080",
    "retry_attempted": true
  }
}
```

### 503 Service Unavailable
```json
{
  "error": "service_unavailable",
  "message": "Image generation service temporarily unavailable",
  "details": {
    "retry_after_seconds": 30,
    "fallback_available": true
  }
}
```

### 500 Internal Server Error
```json
{
  "error": "internal_error",
  "message": "An unexpected error occurred",
  "details": {"request_id": "uuid"}
}
```