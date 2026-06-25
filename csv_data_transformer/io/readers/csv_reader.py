"""CSV data reader."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from csv_data_transformer.config.models import FileOptions
from csv_data_transformer.exceptions import ErrorDetail, FileGuardError
from csv_data_transformer.io.file_guards import (
    assert_file_size_within_limit,
    assert_source_file_exists,
    file_size_mb,
)
from csv_data_transformer.io.readers.base import DataReader

logger = logging.getLogger(__name__)


def _coerce_options(file_options: FileOptions | dict[str, Any]) -> FileOptions:
    if isinstance(file_options, FileOptions):
        return file_options
    return FileOptions.model_validate(file_options)


class CsvDataReader(DataReader):
    """Reads CSV source files with per-connection file_options."""

    def read(self, path: Path, file_options: FileOptions | dict[str, Any]) -> pd.DataFrame:
        options = _coerce_options(file_options)
        resolved = path.expanduser().resolve()

        assert_source_file_exists(resolved)
        assert_file_size_within_limit(resolved, options.max_file_size_mb)

        logger.info(
            "Reading source file path=%s size_mb=%.4f encoding=%s delimiter=%r",
            resolved.name,
            file_size_mb(resolved),
            options.encoding,
            options.delimiter,
        )

        try:
            return pd.read_csv(
                resolved,
                encoding=options.encoding,
                sep=options.delimiter,
                quotechar=options.quote_char,
                header=0 if options.header_row else None,
            )
        except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            raise FileGuardError(
                message=f"Failed to read source CSV '{resolved.name}': {exc}",
                gate="G1",
                details=[ErrorDetail(field="source", message=str(resolved))],
            ) from exc
