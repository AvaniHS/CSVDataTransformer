"""Domain-specific exceptions for fail-first pipeline execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ErrorDetail:
    """Structured detail entry for API error responses."""

    message: str
    field: str | None = None


@dataclass
class TransformerError(Exception):
    """Base error for all domain failures."""

    message: str
    error_code: str = "transformer_error"
    gate: str | None = None
    blueprint_id: str | None = None
    migration_id: str | None = None
    details: list[ErrorDetail] = field(default_factory=list)

    def __str__(self) -> str:
        return self.message


@dataclass
class ConfigValidationError(TransformerError):
    """Raised when config schema or G0 validation fails."""

    error_code: str = "validation_failed"
    gate: str = "G0"


@dataclass
class PipelineError(TransformerError):
    """Raised when pre-flight I/O or orchestration fails."""

    error_code: str = "pipeline_failed"


@dataclass
class FileGuardError(PipelineError):
    """Raised when G1 file checks fail (missing file, size limit, non-empty target)."""

    error_code: str = "io_failed"
    gate: str = "G1"


@dataclass
class TransformError(PipelineError):
    """Raised when filter/join/derivation/mapping/cast fails (G2–G4)."""

    error_code: str = "transform_failed"
    gate: str = "G2"
    phase: str | None = None
    expression: str | None = None
    column: str | None = None


@dataclass
class WriteVerificationError(PipelineError):
    """Raised when G4/G5 write verification fails."""

    error_code: str = "write_verification_failed"
    gate: str = "G4"


def error_details_from_mapping(items: list[dict[str, Any]] | None) -> list[ErrorDetail]:
    """Convert raw detail dicts to ErrorDetail instances."""
    if not items:
        return []
    return [
        ErrorDetail(
            message=str(item.get("message", "")),
            field=item.get("field"),
        )
        for item in items
    ]
