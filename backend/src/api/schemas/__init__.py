"""Shared request and response schema base models."""

from pydantic import BaseModel, ConfigDict


class BaseRequest(BaseModel):
    """Base request model — forbids extra fields by default."""

    model_config = ConfigDict(extra="forbid")


class BaseResponse(BaseModel):
    """Base response model — ignores extra fields by default."""

    model_config = ConfigDict(extra="ignore")
