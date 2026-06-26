"""G0 validation wrapper."""

from __future__ import annotations

from typing import Any

from config_ui.backend.exceptions import ErrorDetail, G0ValidationError


def validate_config_dict(config: dict[str, Any]) -> None:
    """Run JSON Schema + semantic G0 validation using parent engine."""
    try:
        from csv_data_transformer.config.g0_validator import validate_config_semantics
        from csv_data_transformer.config.models import PipelineConfig
        from csv_data_transformer.exceptions import ConfigValidationError
        from csv_data_transformer.pipeline.validator import validate_config_schema_dict
    except ImportError as exc:
        raise G0ValidationError(
            message="Parent csv_data_transformer package is required for G0 validation",
            details=[ErrorDetail(message=str(exc), path="dependencies")],
        ) from exc

    try:
        validate_config_schema_dict(config)
        pipeline = PipelineConfig.model_validate(config)
        validate_config_semantics(pipeline)
    except ConfigValidationError as exc:
        details = [
            ErrorDetail(message=detail.message, path=detail.field)
            for detail in exc.details
        ]
        if not details and exc.message:
            details = [ErrorDetail(message=exc.message, path=None)]
        raise G0ValidationError(
            message=exc.message,
            gate=exc.gate,
            blueprint_id=exc.blueprint_id,
            details=details,
        ) from exc
