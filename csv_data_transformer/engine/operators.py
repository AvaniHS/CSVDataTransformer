"""Operator dispatch for predicates — implemented in Phase 3."""

from __future__ import annotations

from typing import Any

from csv_data_transformer.exceptions import ConfigValidationError

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


def evaluate_predicate(left: Any, operator: str, right: Any | None = None) -> bool:
    """Evaluate a single predicate — full implementation in Phase 3."""
    raise ConfigValidationError(
        message="evaluate_predicate not implemented yet (Phase 3)",
        gate="G0",
    )
