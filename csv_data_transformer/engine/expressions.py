"""Expression parsing and CASE / REGEXP_REPLACE compilation — Phase 4."""

from __future__ import annotations

from csv_data_transformer.exceptions import TransformError


def compile_case_expression(branches: list[dict], else_value: str | None = None) -> str:
    """Compile CASE derivation branches to an evaluable form."""
    raise TransformError(
        message="compile_case_expression not implemented yet (Phase 4)",
        phase="derivations",
    )
