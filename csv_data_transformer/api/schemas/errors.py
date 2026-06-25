"""API error response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": "validation_failed",
                    "message": "JSON Schema validation failed at 'blueprints'",
                    "gate": "G0",
                    "blueprint_id": None,
                    "details": [{"field": "blueprints", "message": "is required"}],
                }
            ]
        }
    )

    error: str = Field(..., examples=["validation_failed"])
    message: str
    gate: str | None = None
    blueprint_id: str | None = None
    details: list[ErrorDetail] = Field(default_factory=list)
