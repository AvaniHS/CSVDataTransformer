"""CSV target writer."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd

from csv_data_transformer.config.models import FileOptions
from csv_data_transformer.exceptions import ErrorDetail, WriteVerificationError
from csv_data_transformer.io.file_guards import assert_target_empty
from csv_data_transformer.io.writers.base import DataTargetWriter

logger = logging.getLogger(__name__)


def _coerce_options(file_options: FileOptions | dict[str, Any]) -> FileOptions:
    if isinstance(file_options, FileOptions):
        return file_options
    return FileOptions.model_validate(file_options)


class CsvDataWriter(DataTargetWriter):
    """Writes CSV target files with atomic temp-file semantics."""

    def write(self, df: pd.DataFrame, path: Path, file_options: FileOptions | dict[str, Any]) -> int:
        options = _coerce_options(file_options)
        resolved = path.expanduser().resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)

        assert_target_empty(resolved, gate="G4")

        temp_path = resolved.parent / f"{resolved.name}.tmp"
        if temp_path.exists():
            temp_path.unlink()

        logger.info(
            "Writing target file path=%s rows=%s encoding=%s",
            resolved.name,
            len(df),
            options.encoding,
        )

        try:
            df.to_csv(
                temp_path,
                index=False,
                encoding=options.encoding,
                sep=options.delimiter,
                quotechar=options.quote_char,
                header=options.header_row,
            )
            bytes_written = temp_path.stat().st_size
            os.replace(temp_path, resolved)
        except OSError as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise WriteVerificationError(
                message=f"Failed to write target CSV '{resolved.name}': {exc}",
                gate="G4",
                details=[ErrorDetail(field="target", message=str(resolved))],
            ) from exc

        logger.info("Wrote target file path=%s bytes=%s", resolved.name, bytes_written)
        return bytes_written
