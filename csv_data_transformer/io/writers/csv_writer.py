"""CSV target writer — implemented in Phase 2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from csv_data_transformer.exceptions import WriteVerificationError
from csv_data_transformer.io.writers.base import DataTargetWriter


class CsvDataWriter(DataTargetWriter):
    """Writes CSV target files with atomic temp-file semantics."""

    def write(self, df: pd.DataFrame, path: Path, file_options: dict[str, Any]) -> int:
        raise WriteVerificationError(
            message=f"CsvDataWriter.write not implemented yet: {path}",
            gate="G4",
        )
