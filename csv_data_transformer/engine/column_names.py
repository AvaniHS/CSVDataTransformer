"""Column name translation between config dot-notation and physical names."""

from __future__ import annotations

import re

from csv_data_transformer.exceptions import ConfigValidationError, ErrorDetail

_QUALIFIED_COLUMN_PATTERN = re.compile(r"^([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)$")
_DERIVATION_REF_PATTERN = re.compile(r"^deriv\.([a-zA-Z_][\w]*)$")
_EXPRESSION_REF_PATTERN = re.compile(r"\b([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)\b")
_PHYSICAL_COLUMN_PATTERN = re.compile(r"^([a-zA-Z_][\w]*)__(.+)$")


def to_physical_column(alias: str, column: str) -> str:
    """Convert alias.column to alias__column."""
    return f"{alias}__{column}"


def to_config_column(alias: str, column: str) -> str:
    """Convert alias and column parts to config qualified reference."""
    return f"{alias}.{column}"


def to_derivation_column(variable_name: str) -> str:
    """Convert derivation variable name to deriv__variable_name."""
    return f"deriv__{variable_name}"


def to_derivation_ref(variable_name: str) -> str:
    """Convert derivation variable name to deriv.variable_name config reference."""
    return f"deriv.{variable_name}"


def parse_qualified_column(reference: str) -> tuple[str, str]:
    """Parse alias.column into (alias, column)."""
    match = _QUALIFIED_COLUMN_PATTERN.match(reference)
    if not match:
        raise ConfigValidationError(
            message=f"Invalid qualified column reference: {reference}",
            gate="G0",
            details=[ErrorDetail(field="reference", message=reference)],
        )
    return match.group(1), match.group(2)


def parse_derivation_ref(reference: str) -> str:
    """Parse deriv.variable_name and return variable_name."""
    match = _DERIVATION_REF_PATTERN.match(reference)
    if not match:
        raise ConfigValidationError(
            message=f"Invalid derivation reference: {reference}",
            gate="G0",
            details=[ErrorDetail(field="reference", message=reference)],
        )
    return match.group(1)


def from_physical_column(physical: str) -> tuple[str, str]:
    """Convert alias__column back to (alias, column)."""
    match = _PHYSICAL_COLUMN_PATTERN.match(physical)
    if not match:
        raise ConfigValidationError(
            message=f"Invalid physical column name: {physical}",
            gate="G0",
            details=[ErrorDetail(field="column", message=physical)],
        )
    return match.group(1), match.group(2)


def resolve_column_reference(reference: str) -> str:
    """Resolve config column or derivation reference to a physical column name."""
    if _DERIVATION_REF_PATTERN.match(reference):
        return to_derivation_column(parse_derivation_ref(reference))
    alias, column = parse_qualified_column(reference)
    return to_physical_column(alias, column)


def prefix_source_columns(columns: list[str], alias: str) -> list[str]:
    """Prefix raw source CSV column names with alias__."""
    return [to_physical_column(alias, column) for column in columns]


def translate_expression(expression: str) -> str:
    """Replace alias.column and deriv.variable references with physical names."""
    return _EXPRESSION_REF_PATTERN.sub(
        lambda match: to_physical_column(match.group(1), match.group(2)),
        expression,
    )
