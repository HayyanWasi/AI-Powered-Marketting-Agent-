"""Unit tests for request validation models."""

import pytest
from pydantic import ValidationError

from src.api.schemas import BaseRequest, BaseResponse


class TestBaseRequest:
    def test_valid_request(self) -> None:
        class TestRequest(BaseRequest):
            name: str
            age: int

        req = TestRequest(name="test", age=30)
        assert req.name == "test"
        assert req.age == 30

    def test_forbids_extra_fields(self) -> None:
        class TestRequest(BaseRequest):
            name: str

        with pytest.raises(ValidationError):
            TestRequest(name="test", extra_field="should_fail")

    def test_requires_required_fields(self) -> None:
        class TestRequest(BaseRequest):
            name: str

        with pytest.raises(ValidationError):
            TestRequest()


class TestBaseResponse:
    def test_valid_response(self) -> None:
        class TestResp(BaseResponse):
            id: str
            value: int

        resp = TestResp(id="abc", value=42)
        assert resp.id == "abc"

    def test_ignores_extra_fields(self) -> None:
        class TestResp(BaseResponse):
            id: str

        resp = TestResp(id="abc", extra_field="ignored")
        assert resp.id == "abc"
        assert not hasattr(resp, "extra_field")
