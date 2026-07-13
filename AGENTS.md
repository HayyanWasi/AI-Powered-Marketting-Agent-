# AI-powered-marketing-agent Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-07-13

## Active Technologies

- Python 3.10+ (project requires >=3.13 per pyproject.toml) + FastAPI, uvicorn, supabase, openai, google-generativeai, (001-project-foundation)

## Project Structure

```text
backend/
  src/
    agents/
    api/routes/
    cache/
    config/
    models/
    services/
  tests/
    unit/
    integration/
frontend/
specs/
```

## Commands

uv run ruff check .; uv run mypy backend/src; uv run pytest

## Code Style

Python 3.10+ (project requires >=3.13 per pyproject.toml): Follow standard conventions

## Recent Changes

- 001-project-foundation: Added Python 3.10+ (project requires >=3.13 per pyproject.toml) + FastAPI, uvicorn, supabase, openai, google-generativeai, Docker, pre-commit, pytest with 100% coverage

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
