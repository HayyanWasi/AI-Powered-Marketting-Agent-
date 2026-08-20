"""Unit tests for API response models and serialization utilities."""


from src.api.response import (
    APIErrorResponse,
    APIResponse,
    ValidationErrorDetail,
    error_response,
    success_response,
)


class TestAPIResponse:
    def test_success_defaults(self) -> None:
        resp = APIResponse()
        assert resp.status == "success"
        assert resp.data is None
        assert resp.message == "OK"
        assert resp.timestamp.endswith("Z")

    def test_success_with_data(self) -> None:
        resp = APIResponse(data={"key": "value"}, message="Created")
        assert resp.data == {"key": "value"}
        assert resp.message == "Created"

    def test_success_serialization(self) -> None:
        resp = APIResponse(data=[1, 2, 3])
        dumped = resp.model_dump()
        assert dumped["status"] == "success"
        assert dumped["data"] == [1, 2, 3]
        assert "timestamp" in dumped


class TestAPIErrorResponse:
    def test_error_defaults(self) -> None:
        resp = APIErrorResponse()
        assert resp.status == "error"
        assert resp.error == "internal_error"
        assert resp.details is None
        assert resp.timestamp.endswith("Z")

    def test_error_with_details(self) -> None:
        resp = APIErrorResponse(
            error="validation_error",
            message="Invalid input",
            details=[ValidationErrorDetail(field="name", message="Required", code="required")],
        )
        assert resp.details is not None
        assert len(resp.details) == 1
        assert resp.details[0].field == "name"

    def test_error_serialization(self) -> None:
        resp = APIErrorResponse(error="not_found", message="Not found")
        dumped = resp.model_dump()
        assert dumped["status"] == "error"
        assert dumped["error"] == "not_found"
        assert "timestamp" in dumped


class TestValidationErrorDetail:
    def test_validation_error(self) -> None:
        detail = ValidationErrorDetail(field="email", message="Invalid email", code="value_error")
        assert detail.field == "email"
        assert detail.message == "Invalid email"
        assert detail.code == "value_error"


class TestHelperFunctions:
    def test_success_response(self) -> None:
        resp = success_response(data="test", message="Done")
        assert isinstance(resp, APIResponse)
        assert resp.data == "test"
        assert resp.message == "Done"

    def test_error_response(self) -> None:
        resp = error_response(error="forbidden", message="Access denied")
        assert isinstance(resp, APIErrorResponse)
        assert resp.error == "forbidden"
        assert resp.message == "Access denied"
