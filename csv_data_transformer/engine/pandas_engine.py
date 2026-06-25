"""Pandas execution engine."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from csv_data_transformer.config.models import (
    CaseDerivation,
    Derivation,
    ExpressionDerivation,
    ExpressionFilter,
    FilterItem,
    JoinConditionItem,
    Mapping,
    RegexpReplaceDerivation,
)
from csv_data_transformer.engine.base import ExecutionEngine
from csv_data_transformer.engine.casting import cast_series, verify_not_all_null, verify_nullable_column
from csv_data_transformer.engine.column_names import resolve_column_reference, to_derivation_column, to_physical_column
from csv_data_transformer.engine.expressions import evaluate_case_derivation, evaluate_dataframe_expression
from csv_data_transformer.engine.joins import extract_merge_key_columns, extract_post_merge_conditions, pandas_join_how
from csv_data_transformer.engine.predicates import apply_dataframe_filters, evaluate_join_conditions
from csv_data_transformer.exceptions import TransformError

logger = logging.getLogger(__name__)


def prefix_dataframe_columns(df: pd.DataFrame, alias: str) -> pd.DataFrame:
    """Prefix raw source columns with alias__."""
    renamed = df.rename(columns=lambda column: to_physical_column(alias, str(column)))
    return renamed.copy()


class PandasExecutionEngine(ExecutionEngine):
    """Concrete strategy using pandas for all DataFrame mutations."""

    def __init__(self, blueprint_id: str | None = None) -> None:
        self.blueprint_id = blueprint_id

    def apply_pre_filters(self, df: pd.DataFrame, filters: list[Any]) -> pd.DataFrame:
        if not filters:
            return df
        rows_before = len(df)
        result = apply_dataframe_filters(df, filters)
        logger.info(
            "Applied pre-filters blueprint_id=%s rows_before=%s rows_after=%s",
            self.blueprint_id,
            rows_before,
            len(result),
        )
        return result

    def apply_join(
        self,
        left: pd.DataFrame,
        right: pd.DataFrame,
        join_type: str,
        conditions: list[Any],
    ) -> pd.DataFrame:
        join_conditions = _coerce_join_conditions(conditions)
        left_on, right_on = extract_merge_key_columns(join_conditions)
        how = pandas_join_how(join_type)

        merged = pd.merge(left, right, left_on=left_on, right_on=right_on, how=how)
        post_merge_conditions = extract_post_merge_conditions(join_conditions)
        if post_merge_conditions:
            mask = evaluate_join_conditions(merged, post_merge_conditions)
            result = merged.loc[mask].copy()
        else:
            result = merged

        logger.info(
            "Applied join blueprint_id=%s join_type=%s rows_after=%s",
            self.blueprint_id,
            join_type,
            len(result),
        )
        return result

    def apply_derivations(self, df: pd.DataFrame, derivations: list[Any]) -> pd.DataFrame:
        if not derivations:
            return df

        result = df.copy()
        for derivation in derivations:
            result = self._apply_derivation(result, _coerce_derivation(derivation))

        logger.info(
            "Applied derivations blueprint_id=%s count=%s rows=%s",
            self.blueprint_id,
            len(derivations),
            len(result),
        )
        return result

    def apply_mappings(self, df: pd.DataFrame, mappings: list[Any]) -> pd.DataFrame:
        if not mappings:
            raise TransformError(
                message="Blueprint must define at least one mapping",
                gate="G2",
                phase="mappings",
                blueprint_id=self.blueprint_id,
            )

        target_columns: dict[str, pd.Series] = {}
        for mapping in (_coerce_mapping(item) for item in mappings):
            series = self._resolve_mapping_source(df, mapping)
            if mapping.default_value is not None:
                series = series.where(series.notna(), mapping.default_value)

            verify_not_all_null(
                series,
                column=mapping.target_column,
                is_nullable=mapping.is_nullable,
                blueprint_id=self.blueprint_id,
            )

            casted = cast_series(
                series,
                mapping.cast_to,
                column=mapping.target_column,
                blueprint_id=self.blueprint_id,
            )
            verify_nullable_column(
                casted,
                column=mapping.target_column,
                is_nullable=mapping.is_nullable,
                blueprint_id=self.blueprint_id,
            )
            target_columns[mapping.target_column] = casted

        result = pd.DataFrame(target_columns)
        logger.info(
            "Applied mappings blueprint_id=%s columns=%s rows=%s",
            self.blueprint_id,
            len(result.columns),
            len(result),
        )
        return result

    def apply_post_filters(self, df: pd.DataFrame, filters: list[Any]) -> pd.DataFrame:
        if not filters:
            return df
        rows_before = len(df)
        result = apply_dataframe_filters(df, filters)
        logger.info(
            "Applied post-filters blueprint_id=%s rows_before=%s rows_after=%s",
            self.blueprint_id,
            rows_before,
            len(result),
        )
        return result

    def _apply_derivation(self, df: pd.DataFrame, derivation: Derivation) -> pd.DataFrame:
        target_column = to_derivation_column(derivation.variable_name)
        result = df.copy()

        if isinstance(derivation, ExpressionDerivation):
            result[target_column] = evaluate_dataframe_expression(
                result,
                derivation.expression,
                phase="derivations",
                blueprint_id=self.blueprint_id,
            )
            return result

        if isinstance(derivation, RegexpReplaceDerivation):
            source_column = resolve_column_reference(derivation.source)
            if source_column not in result.columns:
                raise TransformError(
                    message=f"Source column not found for REGEXP_REPLACE: {derivation.source}",
                    gate="G2",
                    phase="derivations",
                    column=source_column,
                    blueprint_id=self.blueprint_id,
                )
            result[target_column] = (
                result[source_column].astype("string").str.replace(
                    derivation.pattern,
                    derivation.replacement,
                    regex=True,
                )
            )
            return result

        if isinstance(derivation, CaseDerivation):
            result[target_column] = evaluate_case_derivation(
                result,
                derivation,
                blueprint_id=self.blueprint_id,
            )
            return result

        raise TransformError(
            message=f"Unsupported derivation type: {derivation}",
            gate="G2",
            phase="derivations",
            blueprint_id=self.blueprint_id,
        )

    def _resolve_mapping_source(self, df: pd.DataFrame, mapping: Mapping) -> pd.Series:
        if mapping.source_type == "DIRECT":
            physical = resolve_column_reference(mapping.source_value)
            if physical not in df.columns:
                raise TransformError(
                    message=f"Source column not found for DIRECT mapping: {mapping.source_value}",
                    gate="G2",
                    phase="mappings",
                    column=physical,
                    blueprint_id=self.blueprint_id,
                )
            return df[physical]

        if mapping.source_type == "DERIVED":
            physical = resolve_column_reference(mapping.source_value)
            if physical not in df.columns:
                raise TransformError(
                    message=f"Derivation column not found: {mapping.source_value}",
                    gate="G2",
                    phase="mappings",
                    column=physical,
                    blueprint_id=self.blueprint_id,
                )
            return df[physical]

        if mapping.source_type == "EXPRESSION":
            return evaluate_dataframe_expression(
                df,
                mapping.source_value,
                phase="mappings",
                blueprint_id=self.blueprint_id,
            )

        raise TransformError(
            message=f"Unsupported mapping source_type: {mapping.source_type}",
            gate="G2",
            phase="mappings",
            blueprint_id=self.blueprint_id,
        )


def _coerce_join_conditions(conditions: list[Any]) -> list[JoinConditionItem]:
    return conditions  # type: ignore[return-value]


def _coerce_derivation(derivation: Any) -> Derivation:
    return derivation  # type: ignore[return-value]


def _coerce_mapping(mapping: Any) -> Mapping:
    return mapping  # type: ignore[return-value]
