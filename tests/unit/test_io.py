"""Phase 2 I/O layer tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from csv_data_transformer.config.models import Connection, FileOptions
from csv_data_transformer.connections.local_file import LocalFileConnectionResolver
from csv_data_transformer.exceptions import FileGuardError, WriteVerificationError
from csv_data_transformer.io.file_guards import assert_target_empty
from csv_data_transformer.io.readers.csv_reader import CsvDataReader
from csv_data_transformer.io.readers.factory import DataReaderFactory
from csv_data_transformer.io.writers.csv_writer import CsvDataWriter
from csv_data_transformer.io.writers.factory import DataTargetFactory

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EMPLOYEES_CSV = PROJECT_ROOT / "data" / "input" / "employees.csv"


def _connection(base: Path, target: Path) -> Connection:
    return Connection(
        type="LOCAL_FILE_DIRECTORY",
        base_path=str(base),
        target_path=str(target),
    )


def test_csv_reader_reads_fixture() -> None:
    reader = CsvDataReader()
    df = reader.read(EMPLOYEES_CSV, FileOptions())
    assert len(df) == 3
    assert "first_name" in df.columns


def test_csv_reader_custom_delimiter_and_encoding(tmp_path: Path) -> None:
    path = tmp_path / "pipe.csv"
    path.write_text("id|name\n1|Alice\n", encoding="utf-8")
    reader = CsvDataReader()
    df = reader.read(path, FileOptions(delimiter="|"))
    assert list(df.columns) == ["id", "name"]
    assert df.loc[0, "name"] == "Alice"


def test_csv_reader_rejects_missing_file(tmp_path: Path) -> None:
    reader = CsvDataReader()
    with pytest.raises(FileGuardError) as exc_info:
        reader.read(tmp_path / "missing.csv", FileOptions())
    assert exc_info.value.gate == "G1"
    assert "not found" in exc_info.value.message


def test_csv_reader_rejects_file_size_limit(tmp_path: Path) -> None:
    path = tmp_path / "large.csv"
    path.write_bytes(b"x" * (2 * 1024 * 1024))
    reader = CsvDataReader()
    with pytest.raises(FileGuardError) as exc_info:
        reader.read(path, FileOptions(max_file_size_mb=1))
    assert "exceeds max_file_size_mb" in exc_info.value.message


def test_target_empty_guard_allows_missing_and_zero_byte(tmp_path: Path) -> None:
    missing = tmp_path / "out.csv"
    assert_target_empty(missing)

    zero_byte = tmp_path / "zero.csv"
    zero_byte.write_bytes(b"")
    assert_target_empty(zero_byte)


def test_target_empty_guard_rejects_non_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "out.csv"
    path.write_text("data\n", encoding="utf-8")
    with pytest.raises(FileGuardError):
        assert_target_empty(path, gate="G1")


def test_csv_writer_atomic_write_and_target_empty(tmp_path: Path) -> None:
    target_dir = tmp_path / "output"
    target_dir.mkdir()
    output_path = target_dir / "result.csv"
    writer = CsvDataWriter()
    df = pd.DataFrame({"id": [1], "name": ["Alice"]})

    bytes_written = writer.write(df, output_path, FileOptions())
    assert bytes_written > 0
    assert output_path.exists()
    assert not (target_dir / "result.csv.tmp").exists()

    written = pd.read_csv(output_path)
    assert written.loc[0, "name"] == "Alice"


def test_csv_writer_rejects_non_empty_target(tmp_path: Path) -> None:
    output_path = tmp_path / "result.csv"
    output_path.write_text("existing\n", encoding="utf-8")
    writer = CsvDataWriter()
    df = pd.DataFrame({"id": [1]})

    with pytest.raises(WriteVerificationError) as exc_info:
        writer.write(df, output_path, FileOptions())
    assert exc_info.value.gate == "G4"


def test_local_file_connection_resolver_paths(tmp_path: Path) -> None:
    base = tmp_path / "input"
    target = tmp_path / "output"
    base.mkdir()
    target.mkdir()
    resolver = LocalFileConnectionResolver.from_connection(_connection(base, target))

    assert resolver.source_file_path("employees.csv") == base / "employees.csv"
    assert resolver.target_file_path("out.csv") == target / "out.csv"


def test_local_file_connection_resolver_workspace_mode(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    resolver = LocalFileConnectionResolver.from_connection(
        _connection(tmp_path / "ignored", tmp_path / "ignored"),
        workspace_root=workspace,
    )
    assert resolver.base_path == workspace.resolve() / "input"
    assert resolver.target_path == workspace.resolve() / "output"


def test_local_file_resolver_creates_directories(tmp_path: Path) -> None:
    base = tmp_path / "input"
    target = tmp_path / "output"
    resolver = LocalFileConnectionResolver.from_connection(_connection(base, target))
    resolver.ensure_directories()
    assert base.is_dir()
    assert target.is_dir()


def test_reader_and_writer_factories() -> None:
    assert DataReaderFactory.create("CSV").__class__.__name__ == "CsvDataReader"
    assert DataTargetFactory.create("csv").__class__.__name__ == "CsvDataWriter"
