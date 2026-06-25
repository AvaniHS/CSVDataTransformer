"""Validate endpoint response schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ValidateResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "valid": True,
                    "migration_id": "mig-001",
                    "blueprint_count": 2,
                    "output_files": ["employees_export.csv", "departments_export.csv"],
                    "required_files": ["employees.csv", "departments.csv"],
                    "uploaded_files": ["employees.csv", "departments.csv"],
                }
            ]
        }
    )

    valid: bool
    migration_id: str
    blueprint_count: int
    output_files: list[str]
    required_files: list[str]
    uploaded_files: list[str]
