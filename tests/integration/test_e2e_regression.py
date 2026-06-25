"""Golden-file E2E regression tests using tests/fixtures/e2e/."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from csv_data_transformer.api.app import create_app
from csv_data_transformer.cli import main as cli_main
from csv_data_transformer.pipeline.orchestrator import Orchestrator
from tests.support.csv_compare import assert_outputs_match_expected
from tests.support.e2e_workspace import (
    E2E_EXPECTED_DIR,
    E2E_INPUT_DIR,
    E2E_OUTPUT_FILES,
    prepare_e2e_workspace,
)


@pytest.fixture
def api_client() -> TestClient:
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_e2e_orchestrator_outputs_match_expected(tmp_path: Path) -> None:
    """Pipeline orchestrator output must match golden expected CSVs."""
    _config_path, output_dir, workspace_config = prepare_e2e_workspace(tmp_path)

    result = Orchestrator().run(
        workspace_config,
        api_mode=True,
        workspace_root=tmp_path,
        uploaded_files={path.name for path in E2E_INPUT_DIR.glob("*.csv")},
    )

    assert len(result.blueprint_results) == len(E2E_OUTPUT_FILES)
    assert_outputs_match_expected(output_dir, E2E_EXPECTED_DIR, E2E_OUTPUT_FILES)


def test_e2e_cli_outputs_match_expected(tmp_path: Path) -> None:
    """CLI run output must match golden expected CSVs."""
    config_path, output_dir, _workspace_config = prepare_e2e_workspace(tmp_path)

    exit_code = cli_main(["run", "--config", str(config_path)])
    assert exit_code == 0

    assert_outputs_match_expected(output_dir, E2E_EXPECTED_DIR, E2E_OUTPUT_FILES)


def test_e2e_api_zip_outputs_match_expected(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    """API transform ZIP output must match golden expected CSVs."""
    config_path, _output_dir, _workspace_config = prepare_e2e_workspace(tmp_path)

    response = api_client.post(
        "/api/v1/transform",
        files=[
            (
                "config",
                ("config.json", config_path.read_bytes(), "application/json"),
            ),
            *[
                ("files", (path.name, path.read_bytes(), "text/csv"))
                for path in sorted(E2E_INPUT_DIR.glob("*.csv"))
            ],
        ],
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    extract_dir = tmp_path / "api_output"
    extract_dir.mkdir()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(extract_dir)

    assert_outputs_match_expected(extract_dir, E2E_EXPECTED_DIR, E2E_OUTPUT_FILES)
