"""Column name translation between config dot-notation and physical names."""

from __future__ import annotations

import re

_ALIAS_COLUMN_PATTERN = re.compile(r"\b([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)\b")


def to_physical_column(alias: str, column: str) -> str:
    """Convert alias.column to alias__column."""
    return f"{alias}__{column}"


def to_derivation_column(variable_name: str) -> str:
    """Convert derivation variable name to deriv__variable_name."""
    return f"deriv__{variable_name}"


def translate_expression(expression: str) -> str:
    """Replace alias.column references with alias__column in an expression string."""
    return _ALIAS_COLUMN_PATTERN.sub(r"\1__\2", expression)
