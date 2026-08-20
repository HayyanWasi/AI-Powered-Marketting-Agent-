# Data Models: API Layer

## Entity Overview

| Entity | Description | Persistence |
|--------|-------------|-------------|
| APIRequest | Validated HTTP request after FastAPI/Pydantic parsing | None (request-scoped) |
| RequestContext | Metadata attached to every request | None (request-scoped) |
| APIResponse | Standardized JSON envelope for successful responses | None (serialized at runtime) |
| APIErrorResponse | Standardized JSON envelope for error responses | None (serialized at runtime) |
| ValidationError | Structured validation error detail | None (returned in error response) |
| AuthenticatedUser | Resolved user identity from auth token | None (request-scoped) |
| APIVersion | Represents a registered API version | None (runtime config) |

**Note**: The API layer has no persistent data models — it is a stateless routing and validation layer. All business data entities belong to their respective modules (Campaign Management, AI Generation, etc.).

---

## Entity Definitions

### APIRequest

Validated HTTP request after FastAPI/Pydantic parsing.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| path_params | dict[str, Any] | No | URL path parameters |
| query_params | dict[str, Any] | No | Query parameters |
| headers | dict[str, str] | Yes | Request headers |
| body | Any | No | Parsed request body |

**Validation rules**:
- Request body must satisfy the endpoint's Pydantic schema before reaching business logic.
- Unsupported Content-Type returns 415.
- Malformed JSON returns 400.

---

### RequestContext

Metadata attached to every request during processing.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| request_id | str | Yes | Unique request identifier |
| api_version | str | Yes | Requested API version |
| authenticated_user | AuthenticatedUser \| None | No | Authenticated user |
| client_ip | str | Yes | Client IP address |
| start_time | datetime | Yes | Request start timestamp |

---

### APIResponse

Standardized JSON envelope wrapping all successful API responses.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| status | str | Yes | Always `"success"` |
| data | Any | Yes | Response payload (dict, list, or None) |
| message | str | No | Optional informational message |
| timestamp | str | Yes | ISO 8601 timestamp of response generation |

**Validation rules**:
- `status` must be `"success"`
- `data` must be JSON-serializable

---

### APIErrorResponse

Standardized JSON envelope wrapping all error responses.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| status | str | Yes | Always `"error"` |
| error | str | Yes | Machine-readable error type identifier (e.g., `"validation_error"`, `"not_found"`, `"unauthorized"`) |
| message | str | Yes | Human-readable error description |
| details | List[ValidationError] | No | Structured validation error details (if applicable) |
| request_id | str | Yes | Unique request identifier for debugging |
| timestamp | str | Yes | ISO 8601 timestamp of response generation |

**Validation rules**:
- `status` must be `"error"`
- `error` must be a snake_case identifier
- `details` must be null or a list of ValidationError objects

---

### ValidationError

A single structured validation error detail.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| field | str | Yes | Name of the invalid field (dot-notation for nested fields) |
| message | str | Yes | Human-readable error description |
| code | str | Yes | Machine-readable error code (e.g., `"missing_field"`, `"invalid_type"`, `"invalid_format"`, `"value_out_of_range"`) |

**Validation rules**:
- `field` supports dot-notation for nested fields (e.g., `"address.city"`)
- `code` must be a snake_case identifier

---

### AuthenticatedUser

Resolved user identity from authentication token, scoped to the current request.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | Yes | Unique user identifier |
| email | str | Yes | Authenticated email |
| is_active | bool | Yes | Account active flag |
| roles | List[str] | Yes | Assigned roles for authorization |
| permissions | List[str] | Yes | Granted permissions |

**Validation rules**:
- `id` must be a non-empty string
- This is a request-scoped model, not persisted

---

### APIVersion

Represents a registered API version.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | str | Yes | e.g. `"v1"` |
| prefix | str | Yes | URL prefix |
| is_default | bool | Yes | Default version |
| deprecated | bool | Yes | Whether version is deprecated |

---

## Enums

### HTTPStatusGroup

```text
SUCCESS (200-206), REDIRECTION (300-308),
CLIENT_ERROR (400-451), SERVER_ERROR (500-511)

```

### ErrorType

```text
VALIDATION_ERROR, NOT_FOUND, UNAUTHORIZED, FORBIDDEN,
CONFLICT, RATE_LIMITED, INTERNAL_ERROR, BAD_REQUEST,
METHOD_NOT_ALLOWED, NOT_ACCEPTABLE, UNSUPPORTED_MEDIA_TYPE,
PAYLOAD_TOO_LARGE, URI_TOO_LONG

```

---

## Exception-to-HTTP Mapping

| Domain Exception | HTTP Status | Error Type |
| --- | --- | --- |
| `NotFoundError` | 404 | `not_found` |
| `AuthenticationError` | 401 | `unauthorized` |
| `UnauthorizedError` | 401 | `unauthorized` |
| `AuthorizationError` | 403 | `forbidden` |
| `ForbiddenError` | 403 | `forbidden` |
| `ConflictError` | 409 | `conflict` |
| `DomainValidationError` | 422 | `validation_error` |
| `RateLimitError` | 429 | `rate_limited` |
| `UnsupportedMediaTypeError` | 415 | `unsupported_media_type` |
| `PayloadTooLargeError` | 413 | `payload_too_large` |
| `MethodNotAllowedError` | 405 | `method_not_allowed` |
| `NotAcceptableError` | 406 | `not_acceptable` |
| Any unhandled exception | 500 | `internal_error` |

---

## Relationships

```text
Incoming HTTP Request
        │
        ▼
APIRequest (validated by Pydantic schema)
        │
        ▼
[Middleware: CORS, RequestID, Security Headers, Logging, Rate Limiting]
        │
        ▼
[Auth Dependency: authenticate → AuthenticatedUser]
        │
        ▼
[Authorization Dependency: check permissions]
        │
        ▼
[Route Handler (delegates to business module via DI)]
        │
        ▼
Response Envelope (APIResponse or APIErrorResponse)
        │
        ▼
[Exception Handler (if needed)]
        │
        ▼
JSON Serialization
        │
        ▼
HTTP Response

```

---

## Validation Rules

| Entity | Field | Rule |
| --- | --- | --- |
| APIRequest | body | Must satisfy endpoint Pydantic schema before handler execution |
| RequestContext | request_id | Must be unique per request |
| APIResponse | status | Must equal `"success"` |
| APIErrorResponse | status | Must equal `"error"` |
| APIErrorResponse | error | Snake_case identifier |
| ValidationError | field | Dot-notation for nested paths |
| ValidationError | code | Snake_case identifier |
| AuthenticatedUser | id | Non-empty string |

```

```