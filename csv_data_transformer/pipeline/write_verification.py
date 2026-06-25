"""Post-write verification helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from csv_data_transformer.exceptions import ErrorDetail, WriteVerificationError


def verify_post_write(
    path: Path,
    *,
    expected_rows: int,
    blueprint_id: str | None = None,
) -> None:
    """G5: verify output file exists and row count matches expectation."""
    if not path.exists():
        raise WriteVerificationError(
            message=f"Output file missing after write: {path.name}",
            gate="G5",
            blueprint_id=blueprint_id,
            details=[ErrorDetail(field="target", message=str(path))],
        )

    if path.stat().st_size == 0:
        raise WriteVerificationError(
            message=f"Output file is empty after write: {path.name}",
            gate="G5",
            blueprint_id=blueprint_id,
            details=[ErrorDetail(field="target", message=str(path))],
        )

    try:
        written = pd.read_csv(path)
    except Exception as exc:
        raise WriteVerificationError(
            message=f"Failed to read output file for verification: {exc}",
            gate="G5",
            blueprint_id=blueprint_id,
            details=[ErrorDetail(field="target", message=str(path))],
        ) from exc

    if len(written) != expected_rows:
        raise WriteVerificationError(
            message=(
                f"Output row count mismatch for '{path.name}': "
                f"expected {expected_rows}, got {len(written)}"
            ),
            gate="G5",
            blueprint_id=blueprint_id,
            details=[
                ErrorDetail(field="expected_rows", message=str(expected_rows)),
                ErrorDetail(field="actual_rows", message=str(len(written))),
            ],
        )
