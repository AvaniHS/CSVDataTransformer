"""Phase 1 configuration layer tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from csv_data_transformer.config.factory import ConfigReaderFactory
from csv_data_transformer.config.g0_validator import collect_output_files, collect_required_source_files
from csv_data_transformer.config.json_reader import JsonConfigReader
from csv_data_transformer.exceptions import ConfigValidationError
from csv_data_transformer.pipeline.validator import validate_config_schema_dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CONFIG = PROJECT_ROOT / "sampleConfig.json"


def test_load_sample_config_success() -> None:
    config = JsonConfigReader().read(SAMPLE_CONFIG)
    assert config.migration_id == "mig_direct_mapping_demo_2026"
    assert len(config.blueprints) == 2
    assert collect_required_source_files(config) == {"employees.csv", "departments.csv"}
    assert collect_output_files(config) == [
        "employees_export.csv",
        "employees_with_department.csv",
    ]


def test_factory_loads_json_config() -> None:
    reader = ConfigReaderFactory.create(SAMPLE_CONFIG)
    config = reader.read(SAMPLE_CONFIG)
    assert config.blueprints[0].blueprint_id == "bp_direct_one_source_one_target"


def test_invalid_json_file(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ConfigValidationError) as exc_info:
        JsonConfigReader().read(path)
    assert exc_info.value.gate == "G0"
    assert "Invalid JSON" in exc_info.value.message


def test_missing_required_field_fails_schema(tmp_path: Path) -> None:
    data = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    del data["migration_id"]
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigValidationError) as exc_info:
        JsonConfigReader().read(path)
    assert exc_info.value.gate == "G0"
    assert exc_info.value.details


def test_unknown_connection_ref_fails_semantics(tmp_path: Path) -> None:
    data = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    data["blueprints"][0]["sources"]["root_table"]["connection_ref"] = "missing_connection"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigValidationError) as exc_info:
        JsonConfigReader().read(path)
    assert "Unknown connection_ref" in exc_info.value.message


def test_duplicate_blueprint_id_fails_semantics(tmp_path: Path) -> None:
    data = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    data["blueprints"][1]["blueprint_id"] = data["blueprints"][0]["blueprint_id"]
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigValidationError) as exc_info:
        JsonConfigReader().read(path)
    assert "Duplicate blueprint_id" in exc_info.value.message


def test_duplicate_alias_fails_semantics(tmp_path: Path) -> None:
    data = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    data["blueprints"][1]["sources"]["joins"][0]["alias"] = "emp"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigValidationError) as exc_info:
        JsonConfigReader().read(path)
    assert "Duplicate alias" in exc_info.value.message


def test_empty_mappings_fails_semantics(tmp_path: Path) -> None:
    data = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    data["blueprints"][0]["mappings"] = []
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigValidationError) as exc_info:
        JsonConfigReader().read(path)
    assert "mapping" in exc_info.value.message.lower()


def test_invalid_operator_in_join_fails_semantics(tmp_path: Path) -> None:
    data = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    data["blueprints"][1]["sources"]["joins"][0]["conditions"][0]["operator"] = "BETWEEN"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigValidationError) as exc_info:
        JsonConfigReader().read(path)
    assert "Unsupported operator" in exc_info.value.message


def test_validate_config_schema_dict_rejects_non_object() -> None:
    with pytest.raises(ConfigValidationError):
        validate_config_schema_dict([])
