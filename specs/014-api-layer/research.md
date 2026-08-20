# Research: API Layer

## Technology Decisions

### FastAPI for REST Framework

**Decision**: FastAPI with `APIRouter`-based route organization and `Depends()` for dependency injection.

**Rationale**: FastAPI is already the project's web framework (approved by constitution). It provides native async support, automatic OpenAPI generation, built-in Pydantic integration, and a dependency injection system via `Depends()` — all of which align directly with the spec requirements. The project already uses FastAPI, so no new framework dependency is needed.

**Alternatives considered**:
- **Flask**: Requires separate libraries for validation (marshmallow), OpenAPI (flasgger), and async (quart). No built-in DI. More boilerplate for the same result.
- **Starlette directly**: Lower-level, would require building validation and DI from scratch. Not justified.
- **Django REST Framework**: Heavy ORM coupling, not async-first, not aligned with existing project stack.

### URL-Path Versioning

**Decision**: Version via URL prefix (`/api/v1/...`, `/api/v2/...`). Unknown version prefixes return 404.

**Rationale**: URL-path versioning is the clearest approach for API consumers — the version is visible in every request, unambiguous in logs and monitoring, and trivially implemented via FastAPI `APIRouter(prefix="/api/v1")`. The spec explicitly requires this (FR-005).

**Alternatives considered**:
- **Header-based versioning** (`Accept: application/vnd.api+json; version=2`): Invisible in tooling, harder to document, complex to route.
- **Query-parameter versioning** (`?api_version=2`): Easy to omit, pollutes business query params, cache-unfriendly.
- **Content-negotiation versioning**: Same issues as header-based, plus framework support varies.

### Standardized JSON Envelope

**Decision**: All responses wrapped in a consistent envelope. Success: `{ "status": "success", "data": ..., "message": "...", "timestamp": "..." }`. Error: `{ "status": "error", "error": "...", "message": "...", "details": [...], "timestamp": "..." }`.

**Rationale**: Consistent envelope enables a single client-side parsing strategy (User Story 1). The envelope includes `timestamp` for observability. Error details provide machine-readable `field`, `message`, `code` tuples for structured error handling.

**Alternatives considered**:
- **Raw response body**: No envelope — clients must check HTTP status and guess response structure. Violates FR-001.
- **JSON:API specification**: Over-engineered for this project's scope. Enforces complex relationships and resource objects unnecessary for a simple REST layer.

### Global Exception Handlers

**Decision**: Register FastAPI exception handlers at the application level. Map domain exceptions to HTTP status codes via a registry. Catch-all 500 handler sanitizes all unhandled errors.

**Rationale**: Centralized error translation (FR-011) prevents endpoint-level error handling duplication and ensures every error response follows the standardized format (FR-002). Registry-based mapping makes adding new domain exceptions a single-line change.

**Alternatives considered**:
- **Endpoint-level try/except**: Duplication across 10+ endpoints. Risk of inconsistent responses.
- **Middleware-based error catching**: Catches exceptions after response generation, but FastAPI handlers are the idiomatic approach and provide proper context.

### Auth via FastAPI Security Dependencies

**Decision**: Authentication delegated to a reusable `Depends()` callable that validates JWT/OAuth2 tokens. Authorization handled by a separate `Depends()` permission checker.

**Rationale**: FastAPI's `Depends()` system enables reusable, composable security dependencies. The auth dependency validates credentials and returns the authenticated user; the authorization dependency checks permissions against the resource. This separation of concerns aligns with the spec's requirement to delegate auth to an Auth module.

**Alternatives considered**:
- **Middleware-based auth**: Applies auth to every route unconditionally; harder to skip public endpoints.
- **Decorator-based auth**: No built-in FastAPI support; would need custom implementation.

### Request ID and Trace ID Propagation

**Decision**: Middleware generates or extracts `X-Request-ID` and `X-Trace-ID` headers. Propagated to downstream modules via context variables. Exposed in all log entries and error responses.

**Rationale**: Request IDs enable request correlation across services and log aggregation (FR-025). The middleware approach ensures 100% coverage without per-endpoint implementation. Trace IDs connect API requests to Operations module tracing.

**Alternatives considered**:
- **Per-endpoint ID generation**: Inconsistent, easy to miss.
- **Starlette middleware BaseHTTPMiddleware**: Works but FastAPI middleware on the `app` level is simpler for this use case.

## Dependency Summary

| Dependency | Version | Purpose | Already in Project |
|-----------|---------|---------|-------------------|
| fastapi | >=0.110.0 | REST framework | Yes |
| pydantic | >=2.0.0 | Request/response validation | Yes |
| python-multipart | >=0.0.9 | Form/file upload support | Yes |
| httpx | >=0.27.0 | Async test client | Yes |
| uvicorn | >=0.29.0 | ASGI server | Yes |

**No new dependencies required** for the API layer. All dependencies are already present in `pyproject.toml`.

## Integration Points

### Existing Modules (via Dependency Injection)

- **Campaign Management** (`modules/campaigns`) — campaign CRUD endpoints
- **AI Generation Engine** (`modules/ai_generation`) — content generation endpoints
- **Workflow Engine** (`modules/workflow_engine`) — workflow control endpoints
- **Operations** (`modules/operations`) — observability, trace ID propagation, history queries
- **Company Profile** (`services/company_profile`) — brand/profile management endpoints
- **Guest Info Search** (`services/guest_search`) — guest research endpoints
- **Session Cache** (`cache/session_cache`) — session-aware caching (read-only for API)

### Middleware Stack

1. **CORS** — Configurable origins, methods, headers (FR-022)
2. **Request ID** — Generate/propagate `X-Request-ID` and `X-Trace-ID` (FR-025)
3. **Security Headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Cache-Control` (FR-023)
4. **Request Logging** — Log method, path, status, duration per request
5. **Rate Limiting** — Configurable rate limiting (FR-016) — optional, can be toggled via config

## Future Enhancements (Not in Scope)

- WebSocket support for real-time updates
- GraphQL endpoint
- gRPC for internal service-to-service communication
- API key management dashboard
- Usage analytics and billing integration
