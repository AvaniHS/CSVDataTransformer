"""Pandas execution engine — implemented in Phase 4."""

from __future__ import annotations

from typing import Any

import pandas as pd

from csv_data_transformer.engine.base import ExecutionEngine
from csv_data_transformer.exceptions import TransformError


class PandasExecutionEngine(ExecutionEngine):
    """Concrete strategy using pandas for all DataFrame mutations."""

    def apply_pre_filters(self, df: pd.DataFrame, filters: list[Any]) -> pd.DataFrame:
        raise TransformError(message="apply_pre_filters not implemented yet (Phase 4)", phase="pre_filters")

    def apply_join(
        self,
        left: pd.DataFrame,
        right: pd.DataFrame,
        join_type: str,
        conditions: list[Any],
    ) -> pd.DataFrame:
        raise TransformError(message="apply_join not implemented yet (Phase 4)", phase="joins")

    def apply_derivations(self, df: pd.DataFrame, derivations: list[Any]) -> pd.DataFrame:
        raise TransformError(message="apply_derivations not implemented yet (Phase 4)", phase="derivations")

    def apply_mappings(self, df: pd.DataFrame, mappings: list[Any]) -> pd.DataFrame:
        raise TransformError(message="apply_mappings not implemented yet (Phase 4)", phase="mappings")

    def apply_post_filters(self, df: pd.DataFrame, filters: list[Any]) -> pd.DataFrame:
        raise TransformError(message="apply_post_filters not implemented yet (Phase 4)", phase="post_filters")
