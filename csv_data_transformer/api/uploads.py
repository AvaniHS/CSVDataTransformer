"""Multipart upload helpers for API routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import UploadFile

from csv_data_transformer.exceptions import ConfigValidationError, ErrorDetail


def _safe_filename(filename: str | None) -> str:
    if not filename:
        raise ConfigValidationError(
            message="Uploaded file must include a filename",
            gate="G0",
            details=[ErrorDetail(field="files", message="missing filename")],
        )
    safe_name = Path(filename).name
    if not safe_name:
        raise ConfigValidationError(
            message="Uploaded file must include a valid filename",
            gate="G0",
            details=[ErrorDetail(field="files", message=filename)],
        )
    return safe_name


async def read_config_upload(config_file: UploadFile) -> dict:
    """Parse uploaded JSON config from multipart form."""
    raw = await config_file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigValidationError(
            message="Config file must be UTF-8 encoded JSON",
            gate="G0",
            details=[ErrorDetail(field="config", message="invalid encoding")],
        ) from exc

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigValidationError(
            message=f"Config file is not valid JSON: {exc.msg}",
            gate="G0",
            details=[ErrorDetail(field="config", message=str(exc.msg))],
        ) from exc

    if not isinstance(parsed, dict):
        raise ConfigValidationError(
            message="Config file must contain a JSON object",
            gate="G0",
            details=[ErrorDetail(field="config", message="expected object")],
        )
    return parsed


async def save_uploaded_files(uploads: list[UploadFile], input_dir: Path) -> set[str]:
    """Save uploaded CSV files into the workspace input directory."""
    if not uploads:
        raise ConfigValidationError(
            message="At least one source CSV file must be uploaded",
            gate="G0",
            details=[ErrorDetail(field="files", message="empty upload list")],
        )

    input_dir.mkdir(parents=True, exist_ok=True)
    saved_names: set[str] = set()
    for upload in uploads:
        filename = _safe_filename(upload.filename)
        destination = input_dir / filename
        destination.write_bytes(await upload.read())
        saved_names.add(filename)
    return saved_names
