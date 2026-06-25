"""Operator dispatch for predicates."""

from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

from csv_data_transformer.exceptions import ConfigValidationError, TransformError

_CANONICAL_OPERATORS = frozenset(
    {
        "==",
        "!=",
        "<",
        "<=",
        ">",
        ">=",
        "IN",
        "NOT_IN",
        "LIKE",
        "NOT_LIKE",
        "IS_NULL",
        "IS_NOT_NULL",
    }
)

_OPERATOR_ALIASES: dict[str, str] = {
    "=": "==",
    "EQ": "==",
    "<>": "!=",
    "NE": "!=",
    "LT": "<",
    "LE": "<=",
    "GT": ">",
    "GE": ">=",
    "NOT IN": "NOT_IN",
    "NOT LIKE": "NOT_LIKE",
    "IS NULL": "IS_NULL",
    "IS NOT NULL": "IS_NOT_NULL",
}

_NULL_OPERATORS = frozenset({"IS_NULL", "IS_NOT_NULL"})
_LIST_OPERATORS = frozenset({"IN", "NOT_IN"})
_PATTERN_OPERATORS = frozenset({"LIKE", "NOT_LIKE"})


def normalize_operator(operator: str) -> str:
    """Normalize operator aliases to canonical form."""
    stripped = operator.strip()
    upper = stripped.upper()
    if stripped in _OPERATOR_ALIASES:
        return _OPERATOR_ALIASES[stripped]
    if upper in _OPERATOR_ALIASES:
        return _OPERATOR_ALIASES[upper]
    canonical = upper.replace(" ", "_")
    if canonical in _CANONICAL_OPERATORS:
        return canonical
    raise ConfigValidationError(
        message=f"Unsupported operator: {operator}",
        gate="G0",
    )


def is_null_value(value: Any) -> bool:
    """Return True when value is null/NaN/NA."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if value is pd.NA:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def sql_like_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert SQL-style LIKE pattern (% and _) to a compiled regex."""
    regex_parts: list[str] = ["^"]
    for char in pattern:
        if char == "%":
            regex_parts.append(".*")
        elif char == "_":
            regex_parts.append(".")
        elif char in r"\.^$*+?{}[]|()":
            regex_parts.append("\\" + char)
        else:
            regex_parts.append(char)
    regex_parts.append("$")
    return re.compile("".join(regex_parts))


def matches_like(value: Any, pattern: str) -> bool:
    """Evaluate SQL-style LIKE for a scalar value."""
    if is_null_value(value):
        return False
    return sql_like_to_regex(pattern).match(str(value)) is not None


def evaluate_predicate(left: Any, operator: str, right: Any | None = None) -> bool:
    """Evaluate a single scalar predicate."""
    canonical = normalize_operator(operator)

    if canonical in _NULL_OPERATORS:
        if canonical == "IS_NULL":
            return is_null_value(left)
        return not is_null_value(left)

    if canonical in _LIST_OPERATORS:
        if not isinstance(right, list):
            raise TransformError(
                message=f"Operator '{canonical}' requires a list literal",
                gate="G2",
                phase="predicates",
            )
        if is_null_value(left):
            return False
        contained = left in right
        return contained if canonical == "IN" else not contained

    if canonical in _PATTERN_OPERATORS:
        if right is None:
            raise TransformError(
                message=f"Operator '{canonical}' requires a pattern literal",
                gate="G2",
                phase="predicates",
            )
        matched = matches_like(left, str(right))
        return matched if canonical == "LIKE" else not matched

    if right is None:
        return False

    if is_null_value(left) or is_null_value(right):
        return False

    if canonical == "==":
        return left == right
    if canonical == "!=":
        return left != right
    if canonical == "<":
        return left < right
    if canonical == "<=":
        return left <= right
    if canonical == ">":
        return left > right
    if canonical == ">=":
        return left >= right

    raise TransformError(
        message=f"Unsupported operator: {operator}",
        gate="G2",
        phase="predicates",
    )


def evaluate_series_predicate(
    left: pd.Series,
    operator: str,
    right: Any | pd.Series | None = None,
) -> pd.Series:
    """Evaluate a predicate across a DataFrame column."""
    canonical = normalize_operator(operator)

    if canonical == "IS_NULL":
        return left.isna()
    if canonical == "IS_NOT_NULL":
        return left.notna()

    if canonical == "IN":
        if not isinstance(right, list):
            raise TransformError(
                message="Operator 'IN' requires a list literal",
                gate="G2",
                phase="predicates",
            )
        return left.isin(right)

    if canonical == "NOT_IN":
        if not isinstance(right, list):
            raise TransformError(
                message="Operator 'NOT_IN' requires a list literal",
                gate="G2",
                phase="predicates",
            )
        return ~left.isin(right)

    if canonical in _PATTERN_OPERATORS:
        if right is None:
            raise TransformError(
                message=f"Operator '{canonical}' requires a pattern literal",
                gate="G2",
                phase="predicates",
            )
        pattern = sql_like_to_regex(str(right))
        string_series = left.astype("string")
        matched = string_series.str.match(pattern.pattern, na=False)
        return matched if canonical == "LIKE" else ~matched

    if right is None:
        raise TransformError(
            message=f"Operator '{canonical}' requires a right-hand value",
            gate="G2",
            phase="predicates",
        )

    if isinstance(right, pd.Series):
        if canonical == "==":
            return left == right
        if canonical == "!=":
            return left != right
        if canonical == "<":
            return left < right
        if canonical == "<=":
            return left <= right
        if canonical == ">":
            return left > right
        if canonical == ">=":
            return left >= right

    if canonical == "==":
        return left == right
    if canonical == "!=":
        return left != right
    if canonical == "<":
        return left < right
    if canonical == "<=":
        return left <= right
    if canonical == ">":
        return left > right
    if canonical == ">=":
        return left >= right

    raise TransformError(
        message=f"Unsupported operator: {operator}",
        gate="G2",
        phase="predicates",
    )
