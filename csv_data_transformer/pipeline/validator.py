"""Config and pre-flight validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

from csv_data_transformer.config.g0_validator import validate_config_semantics
from csv_data_transformer.config.models import PipelineConfig
from csv_data_transformer.exceptions import ConfigValidationError, ErrorDetail

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


def validate_preflight_io(config: PipelineConfig, workspace_input: str) -> None:
    """G1: validate source files and target emptiness — implemented in Phase 5."""
    raise ConfigValidationError(
        message="validate_preflight_io not implemented yet (Phase 5)",
        gate="G1",
        migration_id=config.migration_id,
    )
