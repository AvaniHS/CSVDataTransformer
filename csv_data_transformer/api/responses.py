"""CSV and ZIP HTTP response builders — implemented in Phase 6."""

from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse, Response


def build_csv_response(path: Path, filename: str, headers: dict[str, str] | None = None) -> FileResponse:
    """Return a single CSV file download response."""
    response_headers = headers or {}
    return FileResponse(
        path=path,
        media_type="text/csv",
        filename=filename,
        headers=response_headers,
    )


def build_zip_response(path: Path, headers: dict[str, str] | None = None) -> Response:
    """Return a ZIP archive download response."""
    response_headers = headers or {}
    response_headers.setdefault(
        "Content-Disposition",
        'attachment; filename="transformed_outputs.zip"',
    )
    return FileResponse(
        path=path,
        media_type="application/zip",
        headers=response_headers,
    )
