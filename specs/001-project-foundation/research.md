# Research: Project Foundation - Project Setup & Configuration

## Overview

No NEEDS CLARIFICATION items were present in the spec. All technology choices
are explicitly defined. This research document confirms decisions and documents
best practices for the chosen stack.

## Technology Decisions

### UV Package Manager
- **Decision**: UV for dependency management, virtual environments, and script execution
- **Rationale**: Spec FR-001 mandates UV. UV is faster than pip/poetry, uses
  `pyproject.toml` for project metadata, and generates `uv.lock` for reproducible builds.
- **Alternatives considered**: pip + venv (slower, no lock file), Poetry (heavier, slower)

### Code Quality Tools
- **Decision**: Black (formatting), Ruff (linting), mypy (type checking)
- **Rationale**: Black is zero-config, Ruff is fast (written in Rust), mypy is the
  standard Python type checker. All three are industry standard.
- **Alternatives considered**: flake8 (slower than Ruff), pylint (more verbose),
  pyright (less common in Python ecosystem)

### Testing Framework
- **Decision**: pytest with pytest-cov and pytest-asyncio
- **Rationale**: Industry standard for Python testing. pytest-cov for coverage
  reporting. pytest-asyncio for async FastAPI endpoint testing.
- **Alternatives considered**: unittest (more verbose), nose2 (less maintained)

### Docker Strategy
- **Decision**: Multi-stage Dockerfiles for backend and frontend, docker-compose for local dev
- **Rationale**: Multi-stage reduces image size; docker-compose simplifies local orchestration
- **Alternatives considered**: Single-stage (larger images), no Docker (manual setup only)

### Pre-commit Hooks
- **Decision**: Use pre-commit framework with hooks for Black, Ruff, mypy, and optional pytest
- **Rationale**: Pre-commit is the standard Python tool for git hooks; enforces quality before commits
- **Alternatives considered**: Manual hooks (less maintainable), CI-only checks (catches issues too late)

## Resolved Clarifications

No NEEDS CLARIFICATION markers were present in the spec. All technology choices
are explicitly defined by the user and constitution.