# Quickstart: Project Foundation

## Prerequisites

- Python 3.10+ (3.13 recommended)
- UV package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker (optional, for containerized development)
- Git

## Setup

```bash
# Clone the repository
git clone <repo-url> ai-social-campaign-manager
cd ai-social-campaign-manager

# Install dependencies
uv sync

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Run code quality tools
uv run black .
uv run ruff check .
uv run mypy src/

# Run tests
uv run pytest

# Start the application
uv run uvicorn src.main:app --reload
```

## Docker Setup

```bash
docker-compose up --build
```

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values:

| Variable | Required | Description |
|----------|----------|-------------|
| OPENAI_API_KEY | Yes | OpenAI API key |
| GOOGLE_API_KEY | Yes | Google Gemini API key |
| SUPABASE_URL | Yes | Supabase project URL |
| SUPABASE_KEY | Yes | Supabase API key |
| LOG_LEVEL | No | Logging level (default: INFO) |
| SESSION_TIMEOUT_HOURS | No | Session cache TTL (default: 24) |
| DDGS_TIMEOUT_SECONDS | No | DDGS search timeout (default: 15) |
| DDGS_RATE_LIMIT_SECONDS | No | DDGS rate limit (default: 5) |