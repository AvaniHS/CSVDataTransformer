"""CSV and ZIP HTTP response builders."""

from __future__ import annotations

import zipfile
from pathlib import Path

from fastapi.responses import FileResponse

from csv_data_transformer.pipeline.blueprint_runner import BlueprintRunResult
from csv_data_transformer.pipeline.orchestrator import PipelineRunResult


def build_transform_headers(result: PipelineRunResult, elapsed_ms: int) -> dict[str, str]:
    """Build success response headers for transform endpoints."""
    headers = {
        "X-Migration-Id": result.migration_id,
        "X-Elapsed-Ms": str(elapsed_ms),
    }
    for blueprint_result in result.blueprint_results:
        headers[f"X-Row-Count-{blueprint_result.blueprint_id}"] = str(blueprint_result.row_count)
    return headers


def create_zip_archive(results: list[BlueprintRunResult], zip_path: Path) -> Path:
    """Create a ZIP archive containing all blueprint target CSV files."""
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in results:
            archive.write(item.output_path, arcname=item.target_file_name)
    return zip_path


def build_csv_response(
    path: Path,
    filename: str,
    headers: dict[str, str] | None = None,
) -> FileResponse:
    """Return a single CSV file download response."""
    return FileResponse(
        path=path,
        media_type="text/csv",
        filename=filename,
        headers=headers or {},
    )


def build_zip_response(path: Path, headers: dict[str, str] | None = None) -> FileResponse:
    """Return a ZIP archive download response."""
    response_headers = dict(headers or {})
    response_headers.setdefault(
        "Content-Disposition",
        'attachment; filename="transformed_outputs.zip"',
    )
    return FileResponse(
        path=path,
        media_type="application/zip",
        headers=response_headers,
    )
