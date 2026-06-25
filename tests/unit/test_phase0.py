"""Phase 0 smoke tests."""

from __future__ import annotations

import logging

import pytest
from starlette.testclient import TestClient

from csv_data_transformer.api.app import create_app
from csv_data_transformer.audit.logger import configure_logging, format_context
from csv_data_transformer.config.factory import ConfigReaderFactory
from csv_data_transformer.engine.column_names import to_physical_column, translate_expression
from csv_data_transformer.engine.operators import normalize_operator
from csv_data_transformer.exceptions import ConfigValidationError, TransformError
from csv_data_transformer.io.readers.factory import DataReaderFactory
from csv_data_transformer.io.writers.factory import DataTargetFactory


def test_package_version() -> None:
    from csv_data_transformer import __version__

    assert __version__ == "0.1.0"


def test_domain_exceptions_carry_context() -> None:
    exc = TransformError(
        message="cast failed",
        gate="G4",
        blueprint_id="bp_test",
        phase="mappings",
        column="employee_id",
    )
    assert exc.error_code == "transform_failed"
    assert exc.blueprint_id == "bp_test"
    assert str(exc) == "cast failed"


def test_config_reader_factory_rejects_unknown_extension(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("key: value", encoding="utf-8")
    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigReaderFactory.create(path)
    assert exc_info.value.gate == "G0"


def test_data_reader_factory_creates_csv_reader() -> None:
    reader = DataReaderFactory.create("CSV")
    assert reader.__class__.__name__ == "CsvDataReader"


def test_column_name_translation() -> None:
    assert to_physical_column("emp", "id") == "emp__id"
    assert translate_expression("emp.id == dept.id") == "emp__id == dept__id"


def test_normalize_operator_aliases() -> None:
    assert normalize_operator("=") == "=="
    assert normalize_operator("IS NULL") == "IS_NULL"


def test_configure_logging_sets_level(caplog: pytest.LogCaptureFixture) -> None:
    configure_logging("DEBUG")
    logger = logging.getLogger("csv_data_transformer.test")
    with caplog.at_level(logging.DEBUG):
        logger.debug("checkpoint %s", format_context(migration_id="mig_test", gate="G0"))
    assert "migration_id=mig_test" in caplog.text


def test_health_endpoint() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-Id" in response.headers
