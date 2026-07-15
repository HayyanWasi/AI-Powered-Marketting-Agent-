# AI Social Campaign Manager

An AI-powered social media campaign management platform.

## Architecture

- **Backend**: Python 3.13 + FastAPI
- **Frontend**: Next.js (placeholder)
- **Database**: Supabase
- **AI**: OpenAI + Google Generative AI

## Getting Started

### Prerequisites

- Python 3.13+
- UV package manager
- Docker (optional, for containerized development)

### Local Development

```bash
# Install dependencies
uv sync

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys (SUPABASE_URL, SUPABASE_KEY, etc.)

# Run database migrations (requires Supabase project)
# Execute backend/migrations/001_create_company_profiles.up.sql in your Supabase SQL editor

# Run the backend
uv run uvicorn backend.src.main:app --reload
```

### Docker

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

## Project Structure

```
backend/
  src/
    agents/       # AI agent implementations
    api/          # API routes and middleware
    cache/        # Caching layer
    config/       # Configuration and settings
    models/       # Data models
    services/     # Business logic services
  tests/          # Test suite
frontend/         # Frontend application (placeholder)
specs/            # Feature specifications
```

## Validation

```bash
uv run ruff check .
uv run mypy backend/src
uv run pytest
```
