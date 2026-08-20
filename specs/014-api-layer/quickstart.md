# Quickstart: API Layer

## Prerequisites

- Python 3.13+
- `uv` package manager
- FastAPI, uvicorn, Pydantic v2 (already in pyproject.toml)

---

## Installation

No new dependencies required. All dependencies are already present:

```bash
uv sync

```

---

## Environment Configuration

```bash
# CORS
export CORS_ORIGINS="http://localhost:3000,[https://app.example.com](https://app.example.com)"

# API
export API_PREFIX="/api"
export API_LATEST_VERSION="v1"
export API_RATE_LIMIT="100/minute"
export API_MAX_BODY_SIZE="10485760"  # 10MB

# Authentication
export JWT_SECRET_KEY="change-me"
export JWT_ALGORITHM="HS256"
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES="60"

# Rate Limiting (optional, disable to skip)
export API_RATE_LIMIT_ENABLED="true"

```

---

## Architecture Overview

The API Layer is a stateless cross-cutting infrastructure module. It sits between the frontend/external clients and the business modules, handling cross-cutting concerns only. Every request receives a unique request ID that is propagated through logs, traces, and API responses for debugging.

```text
External Client
      │
      ▼
FastAPI Router
      │
      ▼
Middleware
(CORS, Request ID, Security Headers, Logging)
      │
      ▼
Authentication / Authorization
      │
      ▼
Pydantic Validation
      │
      ▼
Dependency Injection
      │
      ▼
Business Module
      │
      ▼
Response Envelope
      │
      ▼
Exception Handler (if needed)
      │
      ▼
HTTP Response

```

---

## Basic Usage

### Run the API server

```bash
uv run uvicorn backend.src.api.api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload

```

### Access documentation

OpenAPI: `http://<host>:<port>/api/docs`
ReDoc: `http://<host>:<port>/api/redoc`
OpenAPI JSON: `http://<host>:<port>/api/openapi.json`

### Call an endpoint

```bash
# Health checks (no auth required)
curl http://<host>:<port>/api/v1/health
curl http://<host>:<port>/api/v1/live
curl http://<host>:<port>/api/v1/ready

# Expected response:
# {
#   "status": "success",
#   "data": { "status": "healthy" },
#   "message": "OK",
#   "request_id": "req-12345",
#   "timestamp": "2026-07-19T00:00:00Z"
# }

# Protected endpoint (with auth)
curl -H "Authorization: Bearer <token>" \
  http://<host>:<port>/api/v1/campaigns

# Error response (no auth)
curl http://<host>:<port>/api/v1/campaigns
# {
#   "status": "error",
#   "error": "unauthorized",
#   "message": "Authentication required",
#   "details": null,
#   "request_id": "req-12345",
#   "timestamp": "2026-07-19T00:00:00Z"
# }

```

### API Versioning

```bash
# Version 1
GET /api/v1/campaigns

# Future
GET /api/v2/campaigns

```

---

## Testing

```bash
# Unit tests
uv run pytest backend/tests/unit/api/ -v

# Integration tests
uv run pytest backend/tests/integration/api/ -v

# All API tests
uv run pytest backend/tests/unit/api/ backend/tests/integration/api/ -v

# Coverage
uv run pytest \
  backend/tests/unit/api/ \
  backend/tests/integration/api/ \
  --cov=backend.src.api \
  --cov-report=term

# Load tests
locust -f backend/tests/load/locustfile.py

```

---

## Key Design Decisions

* **Stateless** — No server-side session state. All requests are independently processed.
* **Thin API Layer** — Routes contain no business logic and simply delegate to modules.
* **Async First** — All request handlers and downstream module calls use async APIs where supported.
* **DI-First** — All business module dependencies are injected via `Depends()`. No endpoint instantiates services directly.
* **Versioned Routes** — All endpoints are registered under versioned prefixes (`/api/v1/...`). Unknown versions return 404.
* **Consistent Envelope** — Every response, success or error, follows the same JSON structure.
* **Auto-Documented** — OpenAPI, Swagger UI, and ReDoc are generated automatically from endpoint definitions and Pydantic schemas.
* **Middleware Stack** — CORS, request ID, security headers, logging, and rate limiting are applied globally, not per-endpoint.
* **Observability** — Request IDs, tracing, logging, and metrics are delegated to the Platform & Operations module.

---

## Public Interface

Primary application entry point:

```python
# FastAPI application factory
backend.src.api.api:app

```

The following submodules are considered internal implementation details:

* `dependencies.py` — Auth/DI dependencies
* `middleware.py` — Middleware configuration
* `exception_handlers.py` — Error translation
* `response.py` — Response envelope models
* `v1/` — Version 1 routers
* `v2/` — Version 2 routers (future)

External modules must not import these internal submodules directly.
