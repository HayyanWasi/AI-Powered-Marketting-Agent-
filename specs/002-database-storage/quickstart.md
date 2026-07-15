# Quickstart: Database & Storage Setup

## Prerequisites

- Python 3.13, UV installed
- Supabase project with PostgreSQL and Storage enabled
- `.env` file with `SUPABASE_URL` and `SUPABASE_KEY`

## Setup

```bash
# Install dependencies (python-multipart for file uploads)
uv sync
```

## Manual Smoke Test

```bash
# Start the backend
uv run uvicorn src.main:app --reload
```

### Test Create Company Profile

```bash
curl -X POST http://localhost:8000/api/company \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "tone": "Professional and innovative"}'
```

### Test Upload Brand Images

```bash
curl -X POST http://localhost:8000/api/company/{id}/brand-images \
  -F "images=@/path/to/logo.png" \
  -F "images=@/path/to/style.png"
```

### Test Get/Update/Delete

```bash
# Get profile
curl http://localhost:8000/api/company/{id}

# Update profile
curl -X PUT http://localhost:8000/api/company/{id} \
  -H "Content-Type: application/json" \
  -d '{"tone": "Modern and bold"}'

# Delete profile
curl -X DELETE http://localhost:8000/api/company/{id}
```

## Run Migrations

```bash
# Apply migration (via Supabase SQL editor or psql)
psql "$SUPABASE_URL" -f backend/migrations/001_create_company_profiles.up.sql

# Rollback
psql "$SUPABASE_URL" -f backend/migrations/001_create_company_profiles.down.sql
```

## Run Tests

```bash
uv run pytest backend/tests/ -v --cov=src
```
