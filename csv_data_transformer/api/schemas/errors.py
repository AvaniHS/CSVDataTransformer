"""API error response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    error: str = Field(..., examples=["validation_failed"])
    message: str
    gate: str | None = None
    blueprint_id: str | None = None
    details: list[ErrorDetail] = Field(default_factory=list)
