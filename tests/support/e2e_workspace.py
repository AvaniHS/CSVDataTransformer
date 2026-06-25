"""Prepare isolated workspaces for E2E golden-file regression tests."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

E2E_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "e2e"
E2E_CONFIG_PATH = E2E_FIXTURE_ROOT / "config.json"
E2E_INPUT_DIR = E2E_FIXTURE_ROOT / "input"
E2E_EXPECTED_DIR = E2E_FIXTURE_ROOT / "expected"

E2E_OUTPUT_FILES = [
    "employees_export.csv",
    "employees_with_department.csv",
]


def load_e2e_config() -> dict:
    """Load the E2E fixture config JSON."""
    with E2E_CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def prepare_e2e_workspace(tmp_path: Path) -> tuple[Path, Path, dict]:
    """Copy fixture inputs and write a workspace-scoped config under tmp_path."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    for source_file in E2E_INPUT_DIR.glob("*.csv"):
        shutil.copy(source_file, input_dir / source_file.name)

    workspace_config = deepcopy(load_e2e_config())
    connection = workspace_config["connections"]["local_file_system"]
    connection["base_path"] = str(input_dir)
    connection["target_path"] = str(output_dir)

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(workspace_config), encoding="utf-8")
    return config_path, output_dir, workspace_config
