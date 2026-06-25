"""Validate endpoint response schema."""

from __future__ import annotations

from pydantic import BaseModel


class ValidateResponse(BaseModel):
    valid: bool
    migration_id: str
    blueprint_count: int
    output_files: list[str]
    required_files: list[str]
    uploaded_files: list[str]
