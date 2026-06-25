"""JSON configuration reader."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from csv_data_transformer.config.base import ConfigReader
from csv_data_transformer.config.g0_validator import validate_config_semantics
from csv_data_transformer.config.models import PipelineConfig
from csv_data_transformer.exceptions import ConfigValidationError, ErrorDetail
from csv_data_transformer.pipeline.validator import validate_config_schema_dict


class JsonConfigReader(ConfigReader):
    """Reads and validates JSON configuration files."""

    def read(self, path: Path) -> PipelineConfig:
        if not path.exists():
            raise ConfigValidationError(
                message=f"Config file not found: {path}",
                gate="G0",
                details=[ErrorDetail(field="config", message=str(path))],
            )

        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigValidationError(
                message=f"Unable to read config file: {path}",
                gate="G0",
            ) from exc

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ConfigValidationError(
                message=f"Invalid JSON in config file: {exc.msg}",
                gate="G0",
                details=[ErrorDetail(field="config", message=f"line {exc.lineno}, column {exc.colno}")],
            ) from exc

        if not isinstance(data, dict):
            raise ConfigValidationError(
                message="Config root must be a JSON object",
                gate="G0",
            )

        validate_config_schema_dict(data)

        try:
            config = PipelineConfig.model_validate(data)
        except ValidationError as exc:
            raise _pydantic_error_to_config_error(exc) from exc

        validate_config_semantics(config)
        return config


def _pydantic_error_to_config_error(exc: ValidationError) -> ConfigValidationError:
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"]),
            message=error["msg"],
        )
        for error in exc.errors()
    ]
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(part) for part in first.get("loc", ()))
    return ConfigValidationError(
        message=f"Config structure validation failed at '{field}': {first.get('msg', 'invalid value')}",
        gate="G0",
        details=details,
    )
