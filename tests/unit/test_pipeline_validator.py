"""Phase 5 pipeline validator unit tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from csv_data_transformer.config.json_reader import JsonConfigReader
from csv_data_transformer.exceptions import FileGuardError
from csv_data_transformer.pipeline.validator import validate_preflight_io

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_preflight_rejects_missing_source(tmp_path: Path) -> None:
    config = JsonConfigReader().read(PROJECT_ROOT / "sampleConfig.json")
    config.blueprints = config.blueprints[:1]

    (tmp_path / "input").mkdir()
    (tmp_path / "output").mkdir()

    with pytest.raises(FileGuardError) as exc_info:
        validate_preflight_io(config, workspace_root=tmp_path)
    assert exc_info.value.gate == "G1"


def test_preflight_rejects_unreferenced_upload(tmp_path: Path) -> None:
    config = JsonConfigReader().read(PROJECT_ROOT / "sampleConfig.json")
    config.blueprints = config.blueprints[:1]

    input_dir = tmp_path / "input"
    (tmp_path / "output").mkdir()
    input_dir.mkdir()
    shutil.copy(PROJECT_ROOT / "data" / "input" / "employees.csv", input_dir / "employees.csv")

    with pytest.raises(FileGuardError) as exc_info:
        validate_preflight_io(
            config,
            workspace_root=tmp_path,
            uploaded_files={"employees.csv", "extra.csv"},
        )
    assert "not referenced" in exc_info.value.message


def test_preflight_passes_with_required_files(tmp_path: Path) -> None:
    config = JsonConfigReader().read(PROJECT_ROOT / "sampleConfig.json")
    config.blueprints = config.blueprints[:1]

    input_dir = tmp_path / "input"
    (tmp_path / "output").mkdir()
    input_dir.mkdir()
    shutil.copy(PROJECT_ROOT / "data" / "input" / "employees.csv", input_dir / "employees.csv")

    validate_preflight_io(
        config,
        workspace_root=tmp_path,
        uploaded_files={"employees.csv"},
    )
