"""Abstract base for target writers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from csv_data_transformer.config.models import FileOptions


class DataTargetWriter(ABC):
    """Writes transformed DataFrames to target files."""

    @abstractmethod
    def write(self, df: pd.DataFrame, path: Path, file_options: FileOptions | dict[str, Any]) -> int:
        """Write DataFrame to path. Returns bytes written."""
