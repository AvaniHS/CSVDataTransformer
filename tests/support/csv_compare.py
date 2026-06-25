"""Compare generated CSV files against golden expected outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_csv_for_compare(path: Path) -> pd.DataFrame:
    """Load a CSV as string cells with empty strings for missing values."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def assert_csv_matches_expected(actual: Path, expected: Path) -> None:
    """Assert that two CSV files have identical columns, order, and cell values."""
    actual_df = read_csv_for_compare(actual)
    expected_df = read_csv_for_compare(expected)

    pd.testing.assert_frame_equal(
        actual_df,
        expected_df,
        check_dtype=False,
        check_exact=True,
        obj=f"CSV comparison failed: {actual.name}",
    )


def assert_outputs_match_expected(
    output_dir: Path,
    expected_dir: Path,
    file_names: list[str],
) -> None:
    """Compare each generated output file to its golden expected CSV."""
    for file_name in file_names:
        assert_csv_matches_expected(output_dir / file_name, expected_dir / file_name)
