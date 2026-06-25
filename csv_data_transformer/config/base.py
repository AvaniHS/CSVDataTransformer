"""Abstract base for configuration readers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from csv_data_transformer.config.models import PipelineConfig


class ConfigReader(ABC):
    """Reads a configuration document from a file path."""

    @abstractmethod
    def read(self, path: Path) -> PipelineConfig:
        """Load, validate, and return the parsed configuration."""
