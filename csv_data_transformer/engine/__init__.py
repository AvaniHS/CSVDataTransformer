"""Transformation execution engine."""

from csv_data_transformer.engine.column_names import (
    from_physical_column,
    prefix_source_columns,
    resolve_column_reference,
    to_config_column,
    to_derivation_column,
    to_physical_column,
    translate_expression,
)
from csv_data_transformer.engine.operators import evaluate_predicate, normalize_operator
from csv_data_transformer.engine.predicates import (
    apply_dataframe_filters,
    evaluate_condition_group,
    evaluate_join_condition_item,
    evaluate_join_conditions,
    evaluate_predicate_on_dataframe,
)

from csv_data_transformer.engine.pandas_engine import PandasExecutionEngine, prefix_dataframe_columns

__all__ = [
    "PandasExecutionEngine",
    "apply_dataframe_filters",
    "evaluate_condition_group",
    "evaluate_join_condition_item",
    "evaluate_join_conditions",
    "evaluate_predicate",
    "evaluate_predicate_on_dataframe",
    "from_physical_column",
    "normalize_operator",
    "prefix_dataframe_columns",
    "prefix_source_columns",
    "resolve_column_reference",
    "to_config_column",
    "to_derivation_column",
    "to_physical_column",
    "translate_expression",
]
