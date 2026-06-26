"""CSV parsing and schema inference."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from config_ui.backend.domain.models import CastType, ColumnSchema
from config_ui.backend.exceptions import UploadValidationError

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class TargetParseResult:
    """Parsed target CSV — headers retained; data rows stripped when present."""

    headers: list[str]
    headers_only_bytes: bytes
    data_rows_removed: int


def _infer_cast(values: list[str]) -> CastType:
    if not values:
        return "str"
    non_empty = [value for value in values if value.strip()]
    if not non_empty:
        return "str"
    if all(_is_int(value) for value in non_empty):
        return "int64"
    if all(_is_float(value) for value in non_empty):
        return "float64"
    if all(_DATE_PATTERN.match(value.strip()) for value in non_empty):
        return "datetime64[ns]"
    return "str"


def _is_int(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def parse_source_csv(content: bytes, *, session_id: str, file_name: str) -> tuple[list[ColumnSchema], list[dict[str, str]], int]:
    """Parse source CSV with header and at least one data row."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadValidationError(
            message=f"Source file '{file_name}' must be UTF-8 encoded",
            session_id=session_id,
            file_role="source",
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise UploadValidationError(
            message=f"Source file '{file_name}' is missing a header row",
            session_id=session_id,
            file_role="source",
        )

    headers = [name.strip() for name in reader.fieldnames if name and name.strip()]
    if not headers:
        raise UploadValidationError(
            message=f"Source file '{file_name}' has no column headers",
            session_id=session_id,
            file_role="source",
        )

    rows: list[dict[str, str]] = []
    for row in reader:
        if any(str(value).strip() for value in row.values()):
            rows.append({header: str(row.get(header, "")).strip() for header in headers})

    if not rows:
        raise UploadValidationError(
            message=f"Source file '{file_name}' must contain at least one data row",
            session_id=session_id,
            file_role="source",
        )

    columns: list[ColumnSchema] = []
    for header in headers:
        samples = [row[header] for row in rows[:5]]
        columns.append(
            ColumnSchema(
                name=header,
                inferred_cast=_infer_cast(samples),
                sample_values=samples,
            )
        )

    return columns, rows[:5], len(rows)


def parse_target_csv(content: bytes, *, session_id: str, file_name: str) -> TargetParseResult:
    """Parse target CSV — keep headers only; strip any data rows."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadValidationError(
            message=f"Target file '{file_name}' must be UTF-8 encoded",
            session_id=session_id,
            file_role="target",
        ) from exc

    reader = csv.reader(io.StringIO(text))
    try:
        headers = next(reader)
    except StopIteration as exc:
        raise UploadValidationError(
            message=f"Target file '{file_name}' is empty",
            session_id=session_id,
            file_role="target",
        ) from exc

    cleaned = [header.strip() for header in headers if header and header.strip()]
    if not cleaned:
        raise UploadValidationError(
            message=f"Target file '{file_name}' has no column headers",
            session_id=session_id,
            file_role="target",
        )

    data_rows_removed = 0
    for row in reader:
        if any(cell.strip() for cell in row):
            data_rows_removed += 1

    output = io.StringIO()
    csv.writer(output).writerow(cleaned)
    return TargetParseResult(
        headers=cleaned,
        headers_only_bytes=output.getvalue().encode("utf-8"),
        data_rows_removed=data_rows_removed,
    )


def suggest_alias(file_name: str) -> str:
    """Suggest source alias from filename stem."""
    stem = file_name.rsplit(".", 1)[0].lower()
    alias = re.sub(r"[^a-z0-9_]+", "_", stem).strip("_")
    if not alias or not alias[0].isalpha():
        alias = f"src_{alias or 'table'}"
    return alias[:32]


def default_blueprint_id(target_file_name: str, index: int) -> str:
    stem = target_file_name.rsplit(".", 1)[0].lower()
    slug = re.sub(r"[^a-z0-9_]+", "_", stem).strip("_") or f"target_{index + 1}"
    return f"bp_{slug}"[:48]
