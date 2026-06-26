"""Domain exceptions for config UI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ErrorDetail:
    """Structured detail for API error responses."""

    message: str
    path: str | None = None


@dataclass
class ConfigUIError(Exception):
    """Base error for config UI domain failures."""

    message: str
    error: str = "config_ui_error"
    gate: str | None = None
    blueprint_id: str | None = None
    details: list[ErrorDetail] = field(default_factory=list)

    def __str__(self) -> str:
        return self.message


@dataclass
class SessionError(ConfigUIError):
    """Session not found or invalid."""

    error: str = "session_error"
    session_id: str = ""


@dataclass
class UploadValidationError(ConfigUIError):
    """CSV upload validation failed."""

    error: str = "upload_failed"
    session_id: str = ""
    file_role: str = ""


@dataclass
class ConfigBuildError(ConfigUIError):
    """Config assembly failed."""

    error: str = "build_failed"


@dataclass
class G0ValidationError(ConfigUIError):
    """G0 schema or semantic validation failed."""

    error: str = "validation_failed"
    gate: str = "G0"
