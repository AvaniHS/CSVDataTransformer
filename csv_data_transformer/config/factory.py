"""Factory for ConfigReader implementations."""

from __future__ import annotations

from pathlib import Path

from csv_data_transformer.config.base import ConfigReader
from csv_data_transformer.config.json_reader import JsonConfigReader
from csv_data_transformer.exceptions import ConfigValidationError


class ConfigReaderFactory:
    """Instantiates a ConfigReader based on file extension."""

    @staticmethod
    def create(path: Path) -> ConfigReader:
        suffix = path.suffix.lower()
        if suffix == ".json":
            return JsonConfigReader()
        raise ConfigValidationError(
            message=f"Unsupported config file extension: {suffix}",
            gate="G0",
        )
