"""Pre-flight file guards for source reads and target writes."""

from __future__ import annotations

from pathlib import Path

from csv_data_transformer.exceptions import ErrorDetail, FileGuardError, WriteVerificationError

_BYTES_PER_MB = 1024 * 1024


def assert_source_file_exists(path: Path) -> None:
    """G1: source file must exist."""
    if not path.exists():
        raise FileGuardError(
            message=f"Source file not found: {path.name}",
            gate="G1",
            details=[ErrorDetail(field="source", message=str(path))],
        )
    if not path.is_file():
        raise FileGuardError(
            message=f"Source path is not a file: {path.name}",
            gate="G1",
            details=[ErrorDetail(field="source", message=str(path))],
        )


def assert_file_size_within_limit(path: Path, max_file_size_mb: int) -> None:
    """G1: abort before read when file exceeds configured size limit."""
    size_bytes = path.stat().st_size
    size_mb = size_bytes / _BYTES_PER_MB
    if size_mb > max_file_size_mb:
        raise FileGuardError(
            message=(
                f"Source file '{path.name}' exceeds max_file_size_mb "
                f"({size_mb:.2f} MB > {max_file_size_mb} MB)"
            ),
            gate="G1",
            details=[
                ErrorDetail(field="source", message=str(path)),
                ErrorDetail(field="size_mb", message=f"{size_mb:.2f}"),
            ],
        )


def assert_target_empty(path: Path, *, gate: str = "G1") -> None:
    """G1/G4: target must be absent or zero bytes before write."""
    if not path.exists():
        return

    if path.is_file() and path.stat().st_size == 0:
        return

    error_cls = WriteVerificationError if gate == "G4" else FileGuardError
    raise error_cls(
        message=f"Target file must be empty or absent before write: {path.name}",
        gate=gate,
        details=[ErrorDetail(field="target", message=str(path))],
    )


def file_size_mb(path: Path) -> float:
    """Return file size in megabytes."""
    return path.stat().st_size / _BYTES_PER_MB
