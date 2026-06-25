"""Expression parsing and CASE / REGEXP_REPLACE evaluation."""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from csv_data_transformer.config.models import CaseDerivation
from csv_data_transformer.engine.column_names import (
    is_config_column_reference,
    resolve_column_reference,
    translate_expression,
)
from csv_data_transformer.engine.expression_safety import validate_expression_safety
from csv_data_transformer.exceptions import ErrorDetail, TransformError

_EXPRESSION_HINT_PATTERN = re.compile(r"[\+\-\*/<>=!()]|\b(and|or)\b", re.IGNORECASE)

__all__ = [
    "compile_case_expression",
    "evaluate_case_derivation",
    "evaluate_dataframe_expression",
    "resolve_operand",
    "validate_expression_safety",
]


def _looks_like_expression(value: str) -> bool:
    if is_config_column_reference(value):
        return False
    return bool(_EXPRESSION_HINT_PATTERN.search(value))


def evaluate_dataframe_expression(
    df: pd.DataFrame,
    expression: str,
    *,
    phase: str,
    blueprint_id: str | None = None,
    translate: bool = True,
) -> pd.Series:
    """Evaluate a pandas expression against a DataFrame."""
    validate_expression_safety(expression)
    physical_expression = translate_expression(expression) if translate else expression

    try:
        result = df.eval(physical_expression, engine="python")
    except Exception as exc:
        raise TransformError(
            message=f"Expression evaluation failed: {exc}",
            gate="G2",
            phase=phase,
            expression=expression,
            blueprint_id=blueprint_id,
            details=[ErrorDetail(field="expression", message=physical_expression)],
        ) from exc

    if isinstance(result, pd.DataFrame):
        raise TransformError(
            message="Expression must evaluate to a single column or scalar",
            gate="G2",
            phase=phase,
            expression=expression,
            blueprint_id=blueprint_id,
        )

    if not isinstance(result, pd.Series):
        return pd.Series(result, index=df.index)

    return result


def resolve_operand(
    df: pd.DataFrame,
    value: Any,
    *,
    phase: str,
    blueprint_id: str | None = None,
) -> Any:
    """Resolve a literal, column reference, or expression to a Series or scalar."""
    if not isinstance(value, str):
        return value

    if is_config_column_reference(value):
        physical = resolve_column_reference(value)
        if physical not in df.columns:
            raise TransformError(
                message=f"Column not found for reference '{value}'",
                gate="G2",
                phase=phase,
                column=physical,
                blueprint_id=blueprint_id,
            )
        return df[physical]

    if _looks_like_expression(value):
        return evaluate_dataframe_expression(
            df,
            value,
            phase=phase,
            blueprint_id=blueprint_id,
        )

    return value


def evaluate_case_derivation(
    df: pd.DataFrame,
    derivation: CaseDerivation,
    *,
    blueprint_id: str | None = None,
) -> pd.Series:
    """Evaluate a CASE derivation as nested np.where calls."""
    from csv_data_transformer.engine.predicates import evaluate_join_condition_item

    if derivation.else_value is None:
        result: pd.Series | Any = pd.Series(pd.NA, index=df.index, dtype="object")
    else:
        result = resolve_operand(
            df,
            derivation.else_value,
            phase="derivations",
            blueprint_id=blueprint_id,
        )

    for branch in reversed(derivation.branches):
        mask = evaluate_join_condition_item(df, branch.when)
        then_value = resolve_operand(
            df,
            branch.then,
            phase="derivations",
            blueprint_id=blueprint_id,
        )
        result = pd.Series(np.where(mask, then_value, result), index=df.index)

    return result


def compile_case_expression(branches: list[dict], else_value: str | None = None) -> str:
    """Compile CASE derivation branches to a descriptive nested form for logging."""
    parts = [f"when({branch.get('when')}) then {branch.get('then')}" for branch in branches]
    suffix = f" else {else_value}" if else_value is not None else ""
    return "case " + " ".join(parts) + suffix
