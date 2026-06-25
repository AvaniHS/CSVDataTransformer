"""Join condition parsing for pandas merge."""

from __future__ import annotations

from csv_data_transformer.config.models import ConditionGroup, JoinConditionItem, Predicate
from csv_data_transformer.engine.column_names import resolve_column_reference
from csv_data_transformer.engine.operators import normalize_operator
from csv_data_transformer.exceptions import ErrorDetail, TransformError


def _is_merge_key_predicate(item: JoinConditionItem) -> bool:
    if not isinstance(item, Predicate):
        return False
    operator = normalize_operator(item.operator)
    return operator == "==" and item.right_type == "column" and isinstance(item.right, str)


def _flatten_and_predicates(item: JoinConditionItem) -> list[JoinConditionItem]:
    if isinstance(item, Predicate):
        return [item]
    if isinstance(item, ConditionGroup) and item.logic == "AND":
        flattened: list[JoinConditionItem] = []
        for child in item.conditions:
            flattened.extend(_flatten_and_predicates(child))
        return flattened
    return [item]


def extract_merge_key_columns(
    conditions: list[JoinConditionItem],
) -> tuple[list[str], list[str]]:
    """Extract left_on/right_on column pairs from equality column predicates."""
    left_columns: list[str] = []
    right_columns: list[str] = []

    for condition in conditions:
        for item in _flatten_and_predicates(condition):
            if _is_merge_key_predicate(item):
                left_columns.append(resolve_column_reference(item.left))
                right_columns.append(resolve_column_reference(item.right))

    if not left_columns:
        raise TransformError(
            message="Join requires at least one equality column condition",
            gate="G2",
            phase="joins",
            details=[ErrorDetail(field="conditions", message="no merge keys found")],
        )

    return left_columns, right_columns


def extract_post_merge_conditions(
    conditions: list[JoinConditionItem],
) -> list[JoinConditionItem]:
    """Return join conditions that are not simple equality merge keys."""
    post_merge: list[JoinConditionItem] = []
    for condition in conditions:
        flattened = _flatten_and_predicates(condition)
        if len(flattened) == 1 and _is_merge_key_predicate(flattened[0]):
            continue
        if all(_is_merge_key_predicate(item) for item in flattened):
            continue
        post_merge.append(condition)
    return post_merge


def pandas_join_how(join_type: str) -> str:
    """Map config join_type to pandas merge how parameter."""
    mapping = {
        "LEFT": "left",
        "INNER": "inner",
        "RIGHT": "right",
        "OUTER": "outer",
    }
    normalized = join_type.upper()
    if normalized not in mapping:
        raise TransformError(
            message=f"Unsupported join type: {join_type}",
            gate="G2",
            phase="joins",
        )
    return mapping[normalized]
