# Data Model: Project Foundation - Project Setup & Configuration

## Overview

This foundation feature does not introduce application-level data entities.
The "entities" are configuration files and project metadata structures.

## Configuration Entities

### Project Configuration (`pyproject.toml`)

| Field | Type | Description |
|-------|------|-------------|
| name | string | Project name: "ai-powered-marketing-agent" |
| version | string | Semantic version (current: 0.1.0) |
| requires-python | string | ">=3.13" |
| dependencies | list[string] | Production dependencies |
| dev-dependencies | list[string] | Development dependencies |

### Environment Configuration (`.env`)

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| OPENAI_API_KEY | string | Yes | OpenAI API key for GPT-4o |
| GOOGLE_API_KEY | string | Yes | Google Gemini API key |
| SUPABASE_URL | string | Yes | Supabase project URL |
| SUPABASE_KEY | string | Yes | Supabase API key |
| LOG_LEVEL | string | No | Logging level (default: INFO) |
| SESSION_TIMEOUT_HOURS | int | No | Session cache TTL (default: 24) |
| DDGS_TIMEOUT_SECONDS | int | No | DDGS search timeout (default: 15) |
| DDGS_RATE_LIMIT_SECONDS | int | No | DDGS rate limit (default: 5) |

### Tool Configuration

| Tool | Config Location | Key Settings |
|------|----------------|--------------|
| Black | pyproject.toml | line-length = 100 |
| Ruff | pyproject.toml | line-length = 100, select = ["E", "F", "I", "N", "W"] |
| mypy | pyproject.toml | strict = true |
| pytest | pyproject.toml | testpaths = ["tests"], asyncio_mode = "auto" |
| pytest-cov | pyproject.toml | source = ["src"], report = ["term", "html"] |