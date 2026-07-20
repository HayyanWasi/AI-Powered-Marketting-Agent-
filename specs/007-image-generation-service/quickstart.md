# Quickstart: Pollinations Brand Image Generation

## Prerequisites

- Python 3.13+
- uv (package manager)
- Supabase project with `company_profiles` table (from feature 002)
- Access to Pollinations AI public API (no API key required)

## Local Development Setup

```bash
# Clone and navigate to backend
cd backend

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your Supabase credentials
# Required: SUPABASE_URL, SUPABASE_SERVICE_KEY
```

### Environment Variables (.env)

```bash
# Supabase (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# Pollinations (optional - uses public API)
POLLINATIONS_BASE_URL=https://image.pollinations.ai/prompt
POLLINATIONS_MODEL=kontext
POLLINATIONS_TIMEOUT_SECONDS=30
POLLINATIONS_MAX_RETRIES=3

# Image Validation
MIN_IMAGE_WIDTH=1080
MIN_IMAGE_HEIGHT=1080
IMAGE_VALIDATION_TIMEOUT_SECONDS=10

# API
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

## Running the Service

```bash
# Start development server
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or with Docker
docker-compose up --build
```

## Testing the API

### 1. Health Check
```bash
curl http://localhost:8000/health
# {"status": "healthy", "version": "1.0.0"}
```

### 2. Generate Campaign Image

**Request:**
```bash
curl -X POST http://localhost:8000/api/campaign-images \
  -H "Content-Type: application/json" \
  -d '{
    "company_profile_id": "550e8400-e29b-41d4-a716-446655440000",
    "campaign_prompt": "Summer sale campaign with vibrant colors and modern minimalist design",
    "campaign_context": {
      "platform": "instagram",
      "campaign_type": "seasonal_sale",
      "target_audience": "young professionals"
    }
  }'
```

**Success Response (200):**
```json
{
  "image_url": "https://image.pollinations.ai/prompt/Summer%20sale%20campaign%20with%20vibrant%20colors%20and%20modern%20minimalist%20design%2C%20brand%20colors%20%23FF6B35%20%23004E89%2C%20modern%20minimalist%20style?model=kontext",
  "model": "kontext",
  "generation_time_ms": 12345,
  "fallback_used": false,
  "brand_applied": true,
  "validation": {
    "width": 1024,
    "height": 1024,
    "passed": true
  }
}
```

**Error Response (404 - Profile not found):**
```json
{
  "error": "profile_not_found",
  "message": "Company profile not found",
  "details": {
    "profile_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 3. View Generated Image

Open the `image_url` in a browser or embed in HTML:
```html
<img src="https://image.pollinations.ai/prompt/...?model=kontext" alt="Campaign Image" />
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test categories
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v

# Run with specific marker
uv run pytest -m "not slow" -v
```

## Code Quality Checks

```bash
# Linting
uv run ruff check src/

# Type checking
uv run mypy src/

# Format check
uv run ruff format --check src/
```

## Project Structure (Backend)

```
backend/
├── src/
│   ├── api/routes/campaign_images.py    # POST /api/campaign-images
│   ├── services/
│   │   ├── company_profile_service.py   # Supabase profile queries
│   │   ├── brand_style_service.py       # Brand context extraction
│   │   ├── pollinations_service.py      # Pollinations API client
│   │   └── image_validation_service.py  # Image validation
│   ├── models/
│   │   ├── campaign_image.py            # Request/Response models
│   │   └── brand_style.py               # BrandStyleContext
│   └── main.py                          # FastAPI app
├── tests/
│   ├── unit/
│   │   ├── test_brand_style_service.py
│   │   ├── test_pollinations_service.py
│   │   └── test_image_validation_service.py
│   └── integration/
│       └── test_campaign_image_api.py
└── pyproject.toml
```

## Key Implementation Files

### Services

| Service | Responsibility | Key Methods |
|---------|---------------|-------------|
| `CompanyProfileService` | Fetch company profiles | `get_profile(profile_id)` |
| `BrandStyleService` | Extract brand context, build prompts | `extract_brand_context()`, `build_prompt()` |
| `PollinationsService` | API calls with retry/fallback | `generate_image()`, `generate_fallback()` |
| `ImageValidationService` | Validate image URL and resolution | `validate_image_url()` |

### Models

```python
# CampaignImageRequest
company_profile_id: UUID
campaign_prompt: str (min 10 chars)
campaign_context: CampaignContext (optional)

# CampaignImageResponse
image_url: str (Pollinations CDN)
model: Literal["kontext"]
generation_time_ms: int
fallback_used: bool
brand_applied: bool
validation: ValidationResult
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `404 Profile not found` | Verify `company_profile_id` exists in Supabase `company_profiles` table |
| `503 Service unavailable` | Pollinations API down; fallback will activate automatically |
| `422 Validation failed` | Generated image < 1080x1080; retry happens automatically |
| `Timeout` | Increase `POLLINATIONS_TIMEOUT_SECONDS` (default 30s) |
| `CORS error` | Configure CORS in FastAPI middleware for frontend origin |

### Debug Logging

```bash
# Enable debug logging
LOG_LEVEL=DEBUG uv run uvicorn src.main:app --reload
```

Check logs for:
- Pollinations request/response details
- Retry attempts and backoff timing
- Fallback activation
- Validation results

## API Documentation

Interactive docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Integration with Frontend

```typescript
// Frontend service example
async function generateCampaignImage(data: CampaignImageRequest): Promise<CampaignImageResponse> {
  const response = await fetch('/api/campaign-images', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message);
  }
  
  return response.json();
}

// Usage
const result = await generateCampaignImage({
  company_profile_id: profileId,
  campaign_prompt: "Summer sale with vibrant brand colors",
  campaign_context: { platform: "instagram", campaign_type: "seasonal_sale" }
});

// Display image
<img src={result.image_url} alt="Campaign" />
```

## Performance Notes

- **API overhead**: <500ms p95 (excluding Pollinations generation)
- **Pollinations generation**: 5-25 seconds typical
- **Total timeout**: 30 seconds including retries
- **Concurrent requests**: Tested up to 100 concurrent
- **Caching**: Session cache (24hr TTL) for company profiles

## Deployment Checklist

- [ ] Supabase `company_profiles` table exists with brand fields
- [ ] Environment variables configured in production
- [ ] CORS origins configured for frontend domain
- [ ] Health check endpoint accessible
- [ ] Log aggregation configured (stdout/stderr)
- [ ] Rate limiting considered for Pollinations (IP-based)