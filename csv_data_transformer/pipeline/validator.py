"""Config and pre-flight validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

from csv_data_transformer.config.g0_validator import (
    collect_required_source_files,
    validate_config_semantics,
)
from csv_data_transformer.config.models import Connection, PipelineConfig
from csv_data_transformer.connections.local_file import LocalFileConnectionResolver
from csv_data_transformer.exceptions import ConfigValidationError, ErrorDetail, FileGuardError
from csv_data_transformer.io.file_guards import (
    assert_file_size_within_limit,
    assert_source_file_exists,
    assert_target_empty,
)

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "config.schema.json"
_SCHEMA: dict[str, Any] | None = None
_VALIDATOR: Draft202012Validator | None = None


def _load_schema() -> dict[str, Any]:
    global _SCHEMA, _VALIDATOR
    if _SCHEMA is None:
        with _SCHEMA_PATH.open(encoding="utf-8") as handle:
            _SCHEMA = json.load(handle)
        _VALIDATOR = Draft202012Validator(_SCHEMA)
    return _SCHEMA


def validate_config_schema_dict(data: dict[str, Any]) -> None:
    """G0: validate raw config dict against JSON Schema."""
    _load_schema()
    assert _VALIDATOR is not None
    errors = sorted(_VALIDATOR.iter_errors(data), key=lambda err: list(err.path))
    if not errors:
        return

    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error.path) or "root",
            message=error.message,
        )
        for error in errors[:10]
    ]
    first = errors[0]
    field = ".".join(str(part) for part in first.path) or "root"
    raise ConfigValidationError(
        message=f"JSON Schema validation failed at '{field}': {first.message}",
        gate="G0",
        details=details,
    )


def validate_config(config: PipelineConfig) -> PipelineConfig:
    """G0: re-run semantic validation on an already parsed config."""
    validate_config_semantics(config)
    return config


def validate_config_schema(config: dict[str, Any] | PipelineConfig) -> PipelineConfig:
    """G0: validate config from dict or model and return PipelineConfig."""
    if isinstance(config, PipelineConfig):
        validate_config_semantics(config)
        return config

    validate_config_schema_dict(config)
    pipeline_config = PipelineConfig.model_validate(config)
    validate_config_semantics(pipeline_config)
    return pipeline_config


def _connection_for_source_file(config: PipelineConfig, file_name: str) -> Connection:
    for blueprint in config.blueprints:
        root = blueprint.sources.root_table
        if root.file_name == file_name:
            return config.connections[root.connection_ref]
        for join in blueprint.sources.joins:
            if join.file_name == file_name:
                return config.connections[join.connection_ref]
    raise FileGuardError(
        message=f"No connection found for source file '{file_name}'",
        gate="G1",
        migration_id=config.migration_id,
        details=[ErrorDetail(field="source", message=file_name)],
    )


def validate_preflight_io(
    config: PipelineConfig,
    *,
    workspace_root: Path | None = None,
    uploaded_files: set[str] | None = None,
) -> None:
    """G1: validate source files and target emptiness before pipeline execution."""
    required_sources = collect_required_source_files(config)

    if uploaded_files is not None:
        missing = required_sources - uploaded_files
        if missing:
            raise FileGuardError(
                message=f"Missing required source file(s): {', '.join(sorted(missing))}",
                gate="G1",
                migration_id=config.migration_id,
                details=[ErrorDetail(field="source", message=name) for name in sorted(missing)],
            )
        unreferenced = uploaded_files - required_sources
        if unreferenced:
            raise FileGuardError(
                message=f"Uploaded file(s) not referenced by config: {', '.join(sorted(unreferenced))}",
                gate="G1",
                migration_id=config.migration_id,
                details=[ErrorDetail(field="upload", message=name) for name in sorted(unreferenced)],
            )

    for file_name in sorted(required_sources):
        connection = _connection_for_source_file(config, file_name)
        resolver = LocalFileConnectionResolver.from_connection(
            connection,
            workspace_root=workspace_root,
        )
        source_path = resolver.source_file_path(file_name)
        assert_source_file_exists(source_path)
        assert_file_size_within_limit(source_path, connection.file_options.max_file_size_mb)

    ordered_blueprints = sorted(config.blueprints, key=lambda bp: bp.sequence_order)
    for blueprint in ordered_blueprints:
        connection = config.connections[blueprint.target.connection_ref]
        resolver = LocalFileConnectionResolver.from_connection(
            connection,
            workspace_root=workspace_root,
        )
        target_path = resolver.target_file_path(blueprint.target.file_name)
        assert_target_empty(target_path, gate="G1")
