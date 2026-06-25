"""OpenAPI / Swagger verification tests (REQUIREMENTS §8.8.8)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from starlette.testclient import TestClient

from csv_data_transformer.api.app import create_app

ERROR_RESPONSE_REF = "#/components/schemas/ErrorResponse"


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def schema(client: TestClient) -> dict[str, Any]:
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    return response.json()


def test_docs_loads_without_errors(client: TestClient) -> None:
    response = client.get("/api/v1/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_all_endpoints_visible_under_correct_tags(schema: dict[str, Any]) -> None:
    paths = schema["paths"]

    health = paths["/api/v1/health"]["get"]
    assert health["tags"] == ["Health"]
    assert health["operationId"] == "health_check"

    transform = paths["/api/v1/transform"]["post"]
    validate = paths["/api/v1/validate"]["post"]
    assert transform["tags"] == ["Transform"]
    assert validate["tags"] == ["Transform"]
    assert transform["operationId"] == "transform_csv"
    assert validate["operationId"] == "validate_config"


def test_transform_shows_config_and_files_inputs(schema: dict[str, Any]) -> None:
    body = schema["components"]["schemas"]["Body_transform_csv"]
    assert set(body["required"]) == {"config", "files"}

    config_field = body["properties"]["config"]
    assert config_field["type"] == "string"
    assert "contentMediaType" in config_field

    files_field = body["properties"]["files"]
    assert files_field["type"] == "array"
    assert files_field["items"]["type"] == "string"
    assert files_field["items"].get("format") == "binary"


def test_validate_shows_validate_response_schema(schema: dict[str, Any]) -> None:
    success = schema["paths"]["/api/v1/validate"]["post"]["responses"]["200"]
    ref = success["content"]["application/json"]["schema"]["$ref"]
    assert ref.endswith("/ValidateResponse")

    validate_body = schema["components"]["schemas"]["Body_validate_config"]
    assert set(validate_body["required"]) == {"config", "files"}


def test_error_responses_reference_error_response_with_examples(
    schema: dict[str, Any],
) -> None:
    error_schema = schema["components"]["schemas"]["ErrorResponse"]
    assert "examples" in error_schema
    example = error_schema["examples"][0]
    assert example["error"] == "validation_failed"
    assert example["gate"] == "G0"
    assert example["details"]

    for path in ("/api/v1/transform", "/api/v1/validate"):
        responses = schema["paths"][path]["post"]["responses"]
        for status in ("400", "413", "422", "500"):
            ref = responses[status]["content"]["application/json"]["schema"]["$ref"]
            assert ref == ERROR_RESPONSE_REF


def test_health_shows_health_response_schema(schema: dict[str, Any]) -> None:
    success = schema["paths"]["/api/v1/health"]["get"]["responses"]["200"]
    ref = success["content"]["application/json"]["schema"]["$ref"]
    assert ref.endswith("/HealthResponse")

    health_schema = schema["components"]["schemas"]["HealthResponse"]
    assert "examples" in health_schema
    assert health_schema["examples"][0]["status"] == "ok"


def test_openapi_json_importable(schema: dict[str, Any]) -> None:
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "CSV Data Transformer API"
    assert "version" in schema["info"]
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/transform" in schema["paths"]
    assert "/api/v1/validate" in schema["paths"]
    assert "components" in schema
    assert "schemas" in schema["components"]

    serialized = json.dumps(schema)
    round_trip = json.loads(serialized)
    assert round_trip["openapi"] == schema["openapi"]
