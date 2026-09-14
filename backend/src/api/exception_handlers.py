"""Global exception handlers for the API layer.

Maps domain exceptions to standardized HTTP error responses
with proper status codes and sanitized messages.
"""

import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.response import APIErrorResponse, ValidationErrorDetail


def _get_cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    if origin:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    return {"Access-Control-Allow-Origin": "*"}


async def _error_response(
    request: Request, status_code: int, error: str, message: str
) -> JSONResponse:
    """Build a standardized JSON error response.

    Includes request IDs from middleware for correlation when available.
    """
    body = APIErrorResponse(error=error, message=message).model_dump()
    request_id = request.headers.get("X-Request-ID", "")
    trace_id = request.headers.get("X-Trace-ID", "")
    if request_id:
        body["request_id"] = request_id
    if trace_id:
        body["trace_id"] = trace_id
    headers = _get_cors_headers(request)
    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def _error_response_with_details(
    request: Request,
    status_code: int,
    error: str,
    message: str,
    details: list[ValidationErrorDetail],
) -> JSONResponse:
    """Build a standardized JSON error response with validation details."""
    body = APIErrorResponse(error=error, message=message, details=details).model_dump()
    request_id = request.headers.get("X-Request-ID", "")
    trace_id = request.headers.get("X-Trace-ID", "")
    if request_id:
        body["request_id"] = request_id
    if trace_id:
        body["trace_id"] = trace_id
    headers = _get_cors_headers(request)
    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI request validation errors (422)."""
    details: list[ValidationErrorDetail] = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        code = err.get("type", "validation_error")
        details.append(ValidationErrorDetail(field=field, message=msg, code=code))
    return await _error_response_with_details(
        request, 422, "validation_error", "Request validation failed", details
    )


async def pydantic_validation_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors (422)."""
    details: list[ValidationErrorDetail] = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        code = err.get("type", "validation_error")
        details.append(ValidationErrorDetail(field=field, message=msg, code=code))
    return await _error_response_with_details(
        request, 422, "validation_error", "Request validation failed", details
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Translate Starlette/FastAPI HTTPException to standardized response."""
    status_code = exc.status_code
    error_map: dict[int, str] = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        406: "not_acceptable",
        409: "conflict",
        413: "payload_too_large",
        415: "unsupported_media_type",
        422: "validation_error",
        429: "rate_limited",
    }
    error_type = error_map.get(status_code, "http_error")
    detail = exc.detail

    if isinstance(detail, dict):
        message = detail.get("detail", str(detail))
    elif isinstance(detail, str):
        message = detail
    else:
        message = str(detail) if detail else "HTTP error"

    return await _error_response(request, status_code, error_type, message)


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions.

    Logs the full traceback server-side but returns only a sanitized
    message to the client. Never exposes internal details.
    """
    traceback.print_exc()
    return await _error_response(request, 500, "internal_error", "An unexpected error occurred")


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI application."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
