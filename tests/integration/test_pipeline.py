"""Phase 5 pipeline integration tests."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from csv_data_transformer.pipeline.orchestrator import Orchestrator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CONFIG = PROJECT_ROOT / "sampleConfig.json"
USE_CASE_D_CONFIG = Path(__file__).resolve().parents[1] / "fixtures" / "use_case_d_split.json"
INPUT_DIR = PROJECT_ROOT / "data" / "input"


def _load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _prepare_workspace(
    tmp_path: Path,
    *,
    source_files: list[str],
    config: dict,
) -> tuple[Path, dict]:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    for file_name in source_files:
        shutil.copy(INPUT_DIR / file_name, input_dir / file_name)

    workspace_config = deepcopy(config)
    connection = workspace_config["connections"]["local_file_system"]
    connection["base_path"] = str(input_dir)
    connection["target_path"] = str(output_dir)
    return tmp_path, workspace_config


@pytest.fixture
def orchestrator() -> Orchestrator:
    return Orchestrator()


def test_use_case_a_single_file_transform(orchestrator: Orchestrator, tmp_path: Path) -> None:
    config = _load_config(SAMPLE_CONFIG)
    config["blueprints"] = [config["blueprints"][0]]

    workspace, workspace_config = _prepare_workspace(
        tmp_path,
        source_files=["employees.csv"],
        config=config,
    )

    result = orchestrator.run(
        workspace_config,
        api_mode=True,
        workspace_root=workspace,
        uploaded_files={"employees.csv"},
    )

    assert len(result.blueprint_results) == 1
    output_path = result.blueprint_results[0].output_path
    assert output_path.name == "employees_export.csv"
    assert output_path.exists()

    output_df = pd.read_csv(output_path)
    assert len(output_df) == 3
    assert list(output_df.columns) == ["employee_id", "first_name", "last_name", "email"]


def test_use_case_b_multi_file_join(orchestrator: Orchestrator, tmp_path: Path) -> None:
    config = _load_config(SAMPLE_CONFIG)
    config["blueprints"] = [config["blueprints"][1]]

    workspace, workspace_config = _prepare_workspace(
        tmp_path,
        source_files=["employees.csv", "departments.csv"],
        config=config,
    )

    result = orchestrator.run(
        workspace_config,
        api_mode=True,
        workspace_root=workspace,
        uploaded_files={"employees.csv", "departments.csv"},
    )

    output_df = pd.read_csv(result.blueprint_results[0].output_path)
    assert len(output_df) == 3
    assert "department_name" in output_df.columns
    assert output_df.loc[0, "department_name"] == "Engineering"


def test_join_pre_filters_reduce_lookup_before_merge(orchestrator: Orchestrator, tmp_path: Path) -> None:
    config = _load_config(SAMPLE_CONFIG)
    config["blueprints"] = [config["blueprints"][1]]
    join = config["blueprints"][0]["sources"]["joins"][0]
    join["pre_filters"] = [
        {
            "left": "dept.id",
            "operator": "==",
            "right": 20,
            "right_type": "literal",
        }
    ]

    workspace, workspace_config = _prepare_workspace(
        tmp_path,
        source_files=["employees.csv", "departments.csv"],
        config=config,
    )

    result = orchestrator.run(
        workspace_config,
        api_mode=True,
        workspace_root=workspace,
        uploaded_files={"employees.csv", "departments.csv"},
    )

    output_df = pd.read_csv(result.blueprint_results[0].output_path)
    bob = output_df[output_df["employee_name"] == "Bob Jones"].iloc[0]
    alice = output_df[output_df["employee_name"] == "Alice Smith"].iloc[0]

    assert bob["department_name"] == "Sales"
    assert pd.isna(alice["department_name"]) or alice["department_name"] == ""


def test_use_case_c_multi_blueprint_multi_output(orchestrator: Orchestrator, tmp_path: Path) -> None:
    config = _load_config(SAMPLE_CONFIG)

    workspace, workspace_config = _prepare_workspace(
        tmp_path,
        source_files=["employees.csv", "departments.csv"],
        config=config,
    )

    result = orchestrator.run(
        workspace_config,
        api_mode=True,
        workspace_root=workspace,
        uploaded_files={"employees.csv", "departments.csv"},
    )

    assert len(result.blueprint_results) == 2
    output_names = {item.target_file_name for item in result.blueprint_results}
    assert output_names == {"employees_export.csv", "employees_with_department.csv"}


def test_use_case_d_single_source_split(orchestrator: Orchestrator, tmp_path: Path) -> None:
    config = _load_config(USE_CASE_D_CONFIG)

    workspace, workspace_config = _prepare_workspace(
        tmp_path,
        source_files=["employees.csv"],
        config=config,
    )

    result = orchestrator.run(
        workspace_config,
        api_mode=True,
        workspace_root=workspace,
        uploaded_files={"employees.csv"},
    )

    assert len(result.blueprint_results) == 2
    outputs = {item.target_file_name: item.output_path for item in result.blueprint_results}

    summary = pd.read_csv(outputs["employees_summary.csv"])
    contact = pd.read_csv(outputs["employees_contact.csv"])

    assert list(summary.columns) == ["employee_id", "full_name"]
    assert list(contact.columns) == ["employee_id", "email"]
    assert contact.loc[2, "email"] == "unknown@example.com"
