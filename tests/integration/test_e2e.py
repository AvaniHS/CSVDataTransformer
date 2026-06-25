"""End-to-end tests for API and CLI using sampleConfig.json."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest
from starlette.testclient import TestClient

from csv_data_transformer.api.app import create_app
from csv_data_transformer.cli import main as cli_main

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CONFIG = PROJECT_ROOT / "sampleConfig.json"
INPUT_DIR = PROJECT_ROOT / "data" / "input"


def _prepare_cli_workspace(tmp_path: Path, config: dict) -> Path:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    shutil.copy(INPUT_DIR / "employees.csv", input_dir / "employees.csv")
    shutil.copy(INPUT_DIR / "departments.csv", input_dir / "departments.csv")

    workspace_config = deepcopy(config)
    connection = workspace_config["connections"]["local_file_system"]
    connection["base_path"] = str(input_dir)
    connection["target_path"] = str(output_dir)

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(workspace_config), encoding="utf-8")
    return config_path


@pytest.fixture
def api_client() -> TestClient:
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_cli_validate_sample_config(tmp_path: Path) -> None:
    config = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    config_path = _prepare_cli_workspace(tmp_path, config)

    exit_code = cli_main(["validate", "--config", str(config_path)])
    assert exit_code == 0


def test_cli_run_first_blueprint(tmp_path: Path) -> None:
    config = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    config["blueprints"] = [config["blueprints"][0]]
    config_path = _prepare_cli_workspace(tmp_path, config)
    output_dir = tmp_path / "output"

    exit_code = cli_main(["run", "--config", str(config_path)])
    assert exit_code == 0

    output_file = output_dir / "employees_export.csv"
    assert output_file.exists()
    assert len(pd.read_csv(output_file)) == 3


def test_cli_dry_run_skips_target_writes(tmp_path: Path) -> None:
    config = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    config["blueprints"] = [config["blueprints"][0]]
    config_path = _prepare_cli_workspace(tmp_path, config)
    output_file = tmp_path / "output" / "employees_export.csv"

    exit_code = cli_main(["run", "--config", str(config_path), "--dry-run"])
    assert exit_code == 0
    assert not output_file.exists()


def test_api_full_sample_config_matches_cli_row_counts(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    config = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    config_path = _prepare_cli_workspace(tmp_path, config)

    cli_exit = cli_main(["run", "--config", str(config_path)])
    assert cli_exit == 0

    cli_export = pd.read_csv(tmp_path / "output" / "employees_export.csv")
    cli_joined = pd.read_csv(tmp_path / "output" / "employees_with_department.csv")

    response = api_client.post(
        "/api/v1/transform",
        files=[
            (
                "config",
                (
                    "config.json",
                    config_path.read_bytes(),
                    "application/json",
                ),
            ),
            ("files", ("employees.csv", (INPUT_DIR / "employees.csv").read_bytes(), "text/csv")),
            ("files", ("departments.csv", (INPUT_DIR / "departments.csv").read_bytes(), "text/csv")),
        ],
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    assert len(cli_export) == 3
    assert len(cli_joined) == 3
