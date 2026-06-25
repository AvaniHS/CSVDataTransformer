"""Abstract base for execution engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class ExecutionEngine(ABC):
    """Applies filters, joins, derivations, and mappings to DataFrames."""

    @abstractmethod
    def apply_pre_filters(self, df: pd.DataFrame, filters: list[Any]) -> pd.DataFrame:
        """Apply pre-join filters."""

    @abstractmethod
    def apply_join(
        self,
        left: pd.DataFrame,
        right: pd.DataFrame,
        join_type: str,
        conditions: list[Any],
    ) -> pd.DataFrame:
        """Merge right DataFrame into left using join conditions."""

    @abstractmethod
    def apply_derivations(self, df: pd.DataFrame, derivations: list[Any]) -> pd.DataFrame:
        """Evaluate sequential derivations."""

    @abstractmethod
    def apply_mappings(self, df: pd.DataFrame, mappings: list[Any]) -> pd.DataFrame:
        """Build target DataFrame from mappings."""

    @abstractmethod
    def apply_post_filters(self, df: pd.DataFrame, filters: list[Any]) -> pd.DataFrame:
        """Apply post-mapping filters."""
