"""Abstract base for data readers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd


class DataReader(ABC):
    """Reads source files into DataFrames."""

    @abstractmethod
    def read(self, path: Path, file_options: dict[str, Any]) -> pd.DataFrame:
        """Read a source file and return a DataFrame."""
