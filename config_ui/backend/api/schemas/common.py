"""API response and request schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from config_ui.backend.domain.models import (
    BlueprintState,
    ColumnSchema,
    SessionMetadata,
    SessionState,
    SourceFile,
    TargetFile,
)


class ErrorDetailSchema(BaseModel):
    path: str | None = None
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    gate: str | None = None
    blueprint_id: str | None = None
    details: list[ErrorDetailSchema] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "config-ui"


class SessionCreateRequest(BaseModel):
    metadata: SessionMetadata | None = None


class SessionResponse(BaseModel):
    session_id: str
    metadata: SessionMetadata
    sources: list[SourceFile]
    targets: list[TargetFile]
    blueprints: list[BlueprintState]


class MetadataUpdateRequest(BaseModel):
    metadata: SessionMetadata


class BlueprintUpdateRequest(BaseModel):
    blueprint: BlueprintState


class SourceUploadResponse(BaseModel):
    source: SourceFile


class TargetUploadResponse(BaseModel):
    target: TargetFile
    warning: str | None = None


class ValidateRequest(BaseModel):
    config: dict[str, Any]


class ValidateResponse(BaseModel):
    valid: bool = True
    message: str = "Config passed G0 validation"


class GenerateRequest(BaseModel):
    session_id: str


class GenerateResponse(BaseModel):
    config: dict[str, Any]


class ImportRequest(BaseModel):
    config: dict[str, Any]


class ImportResponse(BaseModel):
    session: SessionResponse


def session_to_response(session: SessionState) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        metadata=session.metadata,
        sources=session.sources,
        targets=session.targets,
        blueprints=session.blueprints,
    )
