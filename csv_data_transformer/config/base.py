"""Abstract base for configuration readers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ConfigReader(ABC):
    """Reads a configuration document from a file path."""

    @abstractmethod
    def read(self, path: Path) -> dict[str, Any]:
        """Load and return the parsed configuration document."""
