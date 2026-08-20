"""Unit tests for global exception handlers."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.exception_handlers import (
    general_exception_handler,
    http_exception_handler,
    register_exception_handlers,
    validation_exception_handler,
)


class TestExceptionHandlerFunctions:
    @pytest.mark.asyncio
    async def test_general_exception_handler_returns_500(self) -> None:
        mock_request = AsyncMock()
        mock_request.headers = {}
        exc = ValueError("test error")
        response = await general_exception_handler(mock_request, exc)
        assert response.status_code == 500
        body = response.body.decode()
        assert '"status":"error"' in body
        assert '"error":"internal_error"' in body
        assert '"message":"An unexpected error occurred"' in body
        assert "ValueError" not in body
        assert "traceback" not in body
        assert "stack" not in body

    @pytest.mark.asyncio
    async def test_http_exception_returns_404(self) -> None:
        mock_request = AsyncMock()
        mock_request.headers = {}
        exc = StarletteHTTPException(status_code=404, detail="Not found")
        response = await http_exception_handler(mock_request, exc)
        assert response.status_code == 404
        body = response.body.decode()
        assert '"status":"error"' in body
        assert '"error":"not_found"' in body

    @pytest.mark.asyncio
    async def test_http_exception_returns_401(self) -> None:
        mock_request = AsyncMock()
        mock_request.headers = {}
        exc = StarletteHTTPException(status_code=401, detail="Unauthorized")
        response = await http_exception_handler(mock_request, exc)
        assert response.status_code == 401
        body = response.body.decode()
        assert '"error":"unauthorized"' in body

    @pytest.mark.asyncio
    async def test_http_exception_returns_403(self) -> None:
        mock_request = AsyncMock()
        mock_request.headers = {}
        exc = StarletteHTTPException(status_code=403, detail="Forbidden")
        response = await http_exception_handler(mock_request, exc)
        assert response.status_code == 403
        body = response.body.decode()
        assert '"error":"forbidden"' in body

    @pytest.mark.asyncio
    async def test_validation_exception_returns_422(self) -> None:
        mock_request = AsyncMock()
        mock_request.headers = {}
        exc = RequestValidationError(
            errors=[
                {"loc": ("body", "name"), "msg": "Field required", "type": "value_error.missing"}
            ]
        )
        response = await validation_exception_handler(mock_request, exc)
        assert response.status_code == 422
        body = response.body.decode()
        assert '"error":"validation_error"' in body
        assert '"field":"body.name"' in body


class TestExceptionHandlerRegistration:
    def test_registration_creates_handlers(self) -> None:
        """Verify that exception_handlers are registered and route errors are caught through integration."""
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/trigger-404")
        async def trigger_404():
            raise StarletteHTTPException(status_code=404, detail="Not found")

        @app.get("/trigger-401")
        async def trigger_401():
            raise StarletteHTTPException(status_code=401, detail="Unauthorized")

        client = TestClient(app)

        resp = client.get("/trigger-404")
        assert resp.status_code == 404
        body = resp.json()
        assert body["status"] == "error"
        assert body["error"] == "not_found"

        resp = client.get("/trigger-401")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"] == "unauthorized"
