"""Predicate and condition-group evaluation for filters and joins."""

from __future__ import annotations

from functools import reduce
from operator import and_, or_
from typing import Any

import pandas as pd

from csv_data_transformer.config.models import (
    ConditionGroup,
    ExpressionFilter,
    FilterItem,
    JoinConditionItem,
    Predicate,
)
from csv_data_transformer.engine.column_names import resolve_column_reference
from csv_data_transformer.engine.operators import evaluate_series_predicate
from csv_data_transformer.exceptions import ErrorDetail, TransformError


def _series_from_reference(df: pd.DataFrame, reference: str) -> pd.Series:
    physical = resolve_column_reference(reference)
    if physical not in df.columns:
        raise TransformError(
            message=f"Column not found for reference '{reference}'",
            gate="G2",
            phase="predicates",
            column=physical,
            details=[ErrorDetail(field="column", message=physical)],
        )
    return df[physical]


def _resolve_right_operand(
    df: pd.DataFrame,
    predicate: Predicate,
) -> Any | pd.Series | None:
    if predicate.right is None:
        return None

    if predicate.right_type == "column":
        if not isinstance(predicate.right, str):
            raise TransformError(
                message="Column right_type requires a string column reference",
                gate="G2",
                phase="predicates",
            )
        return _series_from_reference(df, predicate.right)

    return predicate.right


def evaluate_predicate_on_dataframe(df: pd.DataFrame, predicate: Predicate) -> pd.Series:
    """Evaluate a config predicate against a DataFrame."""
    left = _series_from_reference(df, predicate.left)
    right = _resolve_right_operand(df, predicate)
    return evaluate_series_predicate(left, predicate.operator, right)


def evaluate_condition_group(df: pd.DataFrame, group: ConditionGroup) -> pd.Series:
    """Evaluate a nested AND/OR condition group."""
    masks = [evaluate_join_condition_item(df, item) for item in group.conditions]
    combiner = and_ if group.logic == "AND" else or_
    return reduce(combiner, masks)


def evaluate_join_condition_item(df: pd.DataFrame, item: JoinConditionItem) -> pd.Series:
    """Evaluate a predicate or nested group."""
    if isinstance(item, Predicate):
        return evaluate_predicate_on_dataframe(df, item)
    return evaluate_condition_group(df, item)


def evaluate_join_conditions(df: pd.DataFrame, conditions: list[JoinConditionItem]) -> pd.Series:
    """Evaluate top-level join conditions with implicit AND semantics."""
    if not conditions:
        raise TransformError(
            message="Join conditions must not be empty",
            gate="G2",
            phase="joins",
        )
    masks = [evaluate_join_condition_item(df, item) for item in conditions]
    return reduce(and_, masks)


def evaluate_filter_item(df: pd.DataFrame, item: FilterItem) -> pd.Series:
    """Evaluate a filter predicate or group. Expression filters are Phase 4."""
    if isinstance(item, ExpressionFilter):
        raise TransformError(
            message="Expression filters are not implemented yet (Phase 4)",
            gate="G2",
            phase="filters",
            expression=item.value,
        )
    if isinstance(item, Predicate):
        return evaluate_predicate_on_dataframe(df, item)
    return evaluate_condition_group(df, item)


def apply_dataframe_filters(df: pd.DataFrame, filters: list[FilterItem]) -> pd.DataFrame:
    """Apply each filter entry sequentially (implicit AND across entries)."""
    result = df
    for index, item in enumerate(filters):
        mask = evaluate_filter_item(result, item)
        result = result.loc[mask].copy()
        if result.empty and index < len(filters) - 1:
            break
    return result
