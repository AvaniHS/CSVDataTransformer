"""Abstract base for data readers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from csv_data_transformer.config.models import FileOptions


class DataReader(ABC):
    """Reads source files into DataFrames."""

    @abstractmethod
    def read(self, path: Path, file_options: FileOptions | dict[str, Any]) -> pd.DataFrame:
        """Read a source file and return a DataFrame."""
