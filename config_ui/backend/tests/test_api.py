"""Backend tests for config UI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config_ui.backend.app import create_app
from config_ui.backend.domain.session_service import SessionService
from config_ui.backend.settings import Settings
from config_ui.backend.storage.session_store import SessionStore
from config_ui.backend.validation.csv_parser import parse_target_csv

SAMPLE_CONFIG = Path(__file__).resolve().parents[3] / "sampleConfig.json"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import config_ui.backend.api.dependencies as deps

    deps.get_settings.cache_clear()
    settings = Settings(
        log_level="WARNING",
        workspace_root=tmp_path / "sessions",
        max_upload_mb=5,
        cors_origins=["http://localhost:5173"],
        schema_path=Path(__file__).resolve().parents[3] / "schema" / "config.schema.json",
    )
    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    store = SessionStore(settings)
    monkeypatch.setattr(deps, "get_store", lambda: store)
    monkeypatch.setattr(deps, "get_session_service", lambda: SessionService(store))
    return TestClient(create_app())


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_target_csv_truncates_data_rows() -> None:
    content = b"name,age\nAlice,30\nBob,25\n"
    result = parse_target_csv(content, session_id="abc", file_name="target.csv")
    assert result.headers == ["name", "age"]
    assert result.data_rows_removed == 2
    assert result.headers_only_bytes == b"name,age\r\n"


def test_target_upload_truncates_and_warns(client: TestClient) -> None:
    session = client.post("/api/v1/session", json={"metadata": {"source_count": 0, "target_count": 1}}).json()
    session_id = session["session_id"]

    files = {"file": ("output.csv", "id,name\n1,Alice\n", "text/csv")}
    upload = client.post(f"/api/v1/session/{session_id}/targets", files=files)
    assert upload.status_code == 200
    body = upload.json()
    assert body["target"]["headers"] == ["id", "name"]
    assert "removed" in body["warning"]


def test_session_create_and_upload_source(client: TestClient) -> None:
    session = client.post("/api/v1/session", json={"metadata": {"source_count": 1, "target_count": 1}}).json()
    session_id = session["session_id"]

    files = {"file": ("employees.csv", "id,name\n1,Alice\n2,Bob\n", "text/csv")}
    upload = client.post(f"/api/v1/session/{session_id}/sources", files=files)
    assert upload.status_code == 200
    assert upload.json()["source"]["file_name"] == "employees.csv"
    assert len(upload.json()["source"]["columns"]) == 2


def test_generate_config_mappings_before_post_filters(client: TestClient) -> None:
    config = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    imported = client.post("/api/v1/config/import", json={"config": config})
    assert imported.status_code == 200
    session_id = imported.json()["session"]["session_id"]

    generated = client.post("/api/v1/config/generate", json={"session_id": session_id})
    assert generated.status_code == 200
    payload = generated.json()["config"]
    blueprint = payload["blueprints"][0]
    assert list(blueprint.keys()).index("mappings") < list(blueprint.keys()).index("post_filters")

    validate = client.post("/api/v1/config/validate", json={"config": payload})
    assert validate.status_code == 200
