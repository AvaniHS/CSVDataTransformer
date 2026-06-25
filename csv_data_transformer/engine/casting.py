"""Fail-first dtype casting for mapped columns."""

from __future__ import annotations

import pandas as pd

from csv_data_transformer.config.models import CastType
from csv_data_transformer.exceptions import ErrorDetail, TransformError


def cast_series(
    series: pd.Series,
    cast_to: CastType,
    *,
    column: str,
    blueprint_id: str | None = None,
) -> pd.Series:
    """Cast a series to the configured target dtype; abort on coercion failure."""
    try:
        if cast_to == "str":
            return series.astype("string")
        if cast_to == "int64":
            numeric = pd.to_numeric(series, errors="raise")
            if (numeric % 1 != 0).any():
                raise ValueError("non-integer values present")
            return numeric.astype("int64")
        if cast_to == "float64":
            return pd.to_numeric(series, errors="raise").astype("float64")
        if cast_to == "datetime64[ns]":
            return pd.to_datetime(series, errors="raise")
    except Exception as exc:
        raise TransformError(
            message=f"Cast to '{cast_to}' failed for column '{column}': {exc}",
            gate="G4",
            phase="mappings",
            column=column,
            blueprint_id=blueprint_id,
            details=[ErrorDetail(field="cast_to", message=cast_to)],
        ) from exc

    raise TransformError(
        message=f"Unsupported cast type '{cast_to}' for column '{column}'",
        gate="G4",
        phase="mappings",
        column=column,
        blueprint_id=blueprint_id,
    )


def verify_nullable_column(
    series: pd.Series,
    *,
    column: str,
    is_nullable: bool,
    blueprint_id: str | None = None,
) -> None:
    """G4: abort when a non-nullable column contains null values."""
    if is_nullable:
        return
    if series.isna().any():
        raise TransformError(
            message=f"Non-nullable column '{column}' contains null values",
            gate="G4",
            phase="mappings",
            column=column,
            blueprint_id=blueprint_id,
        )


def verify_not_all_null(
    series: pd.Series,
    *,
    column: str,
    is_nullable: bool,
    blueprint_id: str | None = None,
) -> None:
    """G3: abort when a non-nullable mapping column is entirely null."""
    if is_nullable:
        return
    if series.isna().all():
        raise TransformError(
            message=f"Non-nullable column '{column}' is entirely null",
            gate="G3",
            phase="mappings",
            column=column,
            blueprint_id=blueprint_id,
        )
