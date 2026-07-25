"""API middleware — CORS, request ID, security headers, logging, rate limiting."""

import time
import uuid
from collections import defaultdict
from typing import Callable, Awaitable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Configurable in-memory rate limiting middleware.

    Tracks requests per client IP using a sliding window.
    Returns 429 with Retry-After header when limit exceeded.
    Can be disabled via config.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self.window_seconds

        self._clients[client_ip] = [t for t in self._clients[client_ip] if t > cutoff]

        if len(self._clients[client_ip]) >= self.max_requests:
            response = Response(status_code=429, content='{"status":"error","error":"rate_limited","message":"Rate limit exceeded"}', media_type="application/json")
            response.headers["Retry-After"] = str(self.window_seconds)
            return response

        self._clients[client_ip].append(now)
        return await call_next(request)


class RequestBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding maximum body size with 413 response."""

    def __init__(self, app, max_body_size: int = 10 * 1024 * 1024) -> None:
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return Response(
                status_code=413,
                content='{"status":"error","error":"payload_too_large","message":"Request body exceeds maximum allowed size"}',
                media_type="application/json",
            )
        return await call_next(request)


class ContentTypeValidationMiddleware(BaseHTTPMiddleware):
    """Validate Content-Type for methods with a request body."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if not content_type:
                return Response(
                    status_code=415,
                    content='{"status":"error","error":"unsupported_media_type","message":"Content-Type header is required for POST/PUT/PATCH requests"}',
                    media_type="application/json",
                )
        return await call_next(request)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generate or propagate X-Request-ID and X-Trace-ID headers."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, and duration for each request."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)

        print(f"[API] {request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)")
        return response


def register_middleware(app: FastAPI, enable_rate_limit: bool = True, max_body_size: int = 10 * 1024 * 1024) -> None:
    """Register all middleware on the FastAPI application.

    Middleware executes in reverse registration order (last registered = first executed).
    So the first middleware listed below runs last (innermost).
    """
    app.add_middleware(RequestBodySizeMiddleware, max_body_size=max_body_size)
    app.add_middleware(ContentTypeValidationMiddleware)

    if enable_rate_limit:
        app.add_middleware(RateLimitMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
