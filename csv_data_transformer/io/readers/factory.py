"""Factory for DataReader implementations."""

from __future__ import annotations

from csv_data_transformer.exceptions import ConfigValidationError
from csv_data_transformer.io.readers.base import DataReader
from csv_data_transformer.io.readers.csv_reader import CsvDataReader


class DataReaderFactory:
    """Instantiates a DataReader based on file format."""

    @staticmethod
    def create(file_format: str) -> DataReader:
        normalized = file_format.upper()
        if normalized == "CSV":
            return CsvDataReader()
        raise ConfigValidationError(
            message=f"Unsupported source file format: {file_format}",
            gate="G0",
        )
