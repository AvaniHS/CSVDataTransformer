"""Config and pre-flight validation — implemented in Phase 1/5."""

from __future__ import annotations

from typing import Any

from csv_data_transformer.exceptions import ConfigValidationError


def validate_config_schema(config: dict[str, Any]) -> None:
    """G0: validate config structure."""
    raise ConfigValidationError(
        message="validate_config_schema not implemented yet (Phase 1)",
        gate="G0",
    )


def validate_preflight_io(config: dict[str, Any], workspace_input: str) -> None:
    """G1: validate source files and target emptiness."""
    raise ConfigValidationError(
        message="validate_preflight_io not implemented yet (Phase 5)",
        gate="G1",
    )
