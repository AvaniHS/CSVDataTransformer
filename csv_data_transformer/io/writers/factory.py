"""Factory for DataTargetWriter implementations."""

from __future__ import annotations

from csv_data_transformer.exceptions import ConfigValidationError
from csv_data_transformer.io.writers.base import DataTargetWriter
from csv_data_transformer.io.writers.csv_writer import CsvDataWriter


class DataTargetFactory:
    """Instantiates a DataTargetWriter based on file format."""

    @staticmethod
    def create(file_format: str) -> DataTargetWriter:
        normalized = file_format.upper()
        if normalized == "CSV":
            return CsvDataWriter()
        raise ConfigValidationError(
            message=f"Unsupported target file format: {file_format}",
            gate="G0",
        )
