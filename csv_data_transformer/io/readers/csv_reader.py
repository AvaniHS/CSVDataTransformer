"""CSV data reader — implemented in Phase 2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from csv_data_transformer.exceptions import FileGuardError
from csv_data_transformer.io.readers.base import DataReader


class CsvDataReader(DataReader):
    """Reads CSV source files."""

    def read(self, path: Path, file_options: dict[str, Any]) -> pd.DataFrame:
        raise FileGuardError(
            message=f"CsvDataReader.read not implemented yet: {path}",
            gate="G1",
        )
