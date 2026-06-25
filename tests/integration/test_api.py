"""REST API integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from csv_data_transformer.api.app import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CONFIG = PROJECT_ROOT / "sampleConfig.json"
EMPLOYEES_CSV = PROJECT_ROOT / "data" / "input" / "employees.csv"
DEPARTMENTS_CSV = PROJECT_ROOT / "data" / "input" / "departments.csv"


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _single_blueprint_config() -> dict:
    config = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    config["blueprints"] = [config["blueprints"][0]]
    return config


def _multipart_files(
    config: dict,
    *,
    source_files: list[tuple[str, Path]],
) -> list[tuple[str, tuple[str, bytes, str]]]:
    payload: list[tuple[str, tuple[str, bytes, str]]] = [
        (
            "config",
            (
                "config.json",
                json.dumps(config).encode("utf-8"),
                "application/json",
            ),
        )
    ]
    for filename, path in source_files:
        payload.append(("files", (filename, path.read_bytes(), "text/csv")))
    return payload


def test_openapi_documents_transform_endpoints(client: TestClient) -> None:
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/transform" in paths
    assert "/api/v1/validate" in paths


def test_transform_single_blueprint_returns_csv(client: TestClient) -> None:
    config = _single_blueprint_config()
    response = client.post(
        "/api/v1/transform",
        files=_multipart_files(config, source_files=[("employees.csv", EMPLOYEES_CSV)]),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "X-Migration-Id" in response.headers
    assert "X-Elapsed-Ms" in response.headers
    assert "employee_id" in response.text


def test_validate_returns_metadata(client: TestClient) -> None:
    config = _single_blueprint_config()
    response = client.post(
        "/api/v1/validate",
        files=_multipart_files(config, source_files=[("employees.csv", EMPLOYEES_CSV)]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["blueprint_count"] == 1
    assert body["required_files"] == ["employees.csv"]
    assert body["uploaded_files"] == ["employees.csv"]
    assert body["output_files"] == ["employees_export.csv"]


def test_transform_multi_blueprint_returns_zip(client: TestClient) -> None:
    config = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    response = client.post(
        "/api/v1/transform",
        files=_multipart_files(
            config,
            source_files=[
                ("employees.csv", EMPLOYEES_CSV),
                ("departments.csv", DEPARTMENTS_CSV),
            ],
        ),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.content.startswith(b"PK")


def test_invalid_config_returns_error_shape(client: TestClient) -> None:
    response = client.post(
        "/api/v1/transform",
        files=[
            ("config", ("config.json", b"{not-json", "application/json")),
            ("files", ("employees.csv", EMPLOYEES_CSV.read_bytes(), "text/csv")),
        ],
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "validation_failed"
    assert body["gate"] == "G0"
    assert "message" in body


def test_missing_source_file_returns_400(client: TestClient) -> None:
    config = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    response = client.post(
        "/api/v1/validate",
        files=_multipart_files(config, source_files=[("employees.csv", EMPLOYEES_CSV)]),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["gate"] == "G1"
    assert body["error"] == "io_failed"
