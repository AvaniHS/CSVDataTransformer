"""Session domain models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CastType = Literal["str", "int64", "float64", "datetime64[ns]"]
JoinType = Literal["LEFT", "INNER", "RIGHT", "OUTER"]
SourceType = Literal["DIRECT", "DERIVED", "EXPRESSION"]
TransformType = Literal["EXPRESSION", "REGEXP_REPLACE", "CASE"]


class ColumnSchema(BaseModel):
    name: str
    inferred_cast: CastType = "str"
    sample_values: list[str] = Field(default_factory=list)


class SourceFile(BaseModel):
    source_id: str
    file_name: str
    alias: str
    columns: list[ColumnSchema] = Field(default_factory=list)
    sample_rows: list[dict[str, str]] = Field(default_factory=list)
    row_count: int = 0


class TargetFile(BaseModel):
    target_id: str
    file_name: str
    headers: list[str] = Field(default_factory=list)


class JoinState(BaseModel):
    source_id: str
    join_type: JoinType = "LEFT"
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    pre_filters: list[dict[str, Any]] = Field(default_factory=list)


class MappingState(BaseModel):
    target_column: str
    source_type: SourceType = "DIRECT"
    source_value: str = ""
    cast_to: CastType = "str"
    is_nullable: bool = True
    default_value: Any | None = None


class BlueprintState(BaseModel):
    blueprint_id: str
    sequence_order: int
    target_id: str
    root_source_id: str
    joins: list[JoinState] = Field(default_factory=list)
    pre_filters: list[dict[str, Any]] = Field(default_factory=list)
    pending_join_pre_filters: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    derivations: list[dict[str, Any]] = Field(default_factory=list)
    post_filters: list[dict[str, Any]] = Field(default_factory=list)
    mappings: list[MappingState] = Field(default_factory=list)
    comment: str | None = None


class SessionMetadata(BaseModel):
    migration_id: str = "mig_config_ui"
    client_id: str = "client_default"
    version: str = "1.0.0"
    connection_ref: str = "local_file_system"
    base_path: str | None = None
    target_path: str | None = None
    source_count: int = 1
    target_count: int = 1


class SessionState(BaseModel):
    session_id: str
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)
    sources: list[SourceFile] = Field(default_factory=list)
    targets: list[TargetFile] = Field(default_factory=list)
    blueprints: list[BlueprintState] = Field(default_factory=list)
