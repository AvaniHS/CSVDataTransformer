"""JSON configuration reader — implemented in Phase 1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from csv_data_transformer.config.base import ConfigReader
from csv_data_transformer.exceptions import ConfigValidationError


class JsonConfigReader(ConfigReader):
    """Reads JSON configuration files."""

    def read(self, path: Path) -> dict[str, Any]:
        raise ConfigValidationError(
            message=f"JsonConfigReader.read not implemented yet: {path}",
            gate="G0",
        )
