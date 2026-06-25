"""Phase 4 Pandas execution engine tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from csv_data_transformer.config.models import (
    CaseBranch,
    CaseDerivation,
    ExpressionDerivation,
    ExpressionFilter,
    Mapping,
    Predicate,
    RegexpReplaceDerivation,
)
from csv_data_transformer.engine.casting import cast_series
from csv_data_transformer.engine.expression_safety import validate_expression_safety
from csv_data_transformer.engine.expressions import evaluate_dataframe_expression
from csv_data_transformer.engine.joins import extract_merge_key_columns
from csv_data_transformer.engine.pandas_engine import PandasExecutionEngine, prefix_dataframe_columns
from csv_data_transformer.exceptions import TransformError
from csv_data_transformer.io.readers.csv_reader import CsvDataReader

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EMPLOYEES_CSV = PROJECT_ROOT / "data" / "input" / "employees.csv"
DEPARTMENTS_CSV = PROJECT_ROOT / "data" / "input" / "departments.csv"


@pytest.fixture
def engine() -> PandasExecutionEngine:
    return PandasExecutionEngine(blueprint_id="bp_test")


@pytest.fixture
def employees_df() -> pd.DataFrame:
    raw = CsvDataReader().read(EMPLOYEES_CSV, {})
    return prefix_dataframe_columns(raw, "emp")


@pytest.fixture
def departments_df() -> pd.DataFrame:
    raw = CsvDataReader().read(DEPARTMENTS_CSV, {})
    return prefix_dataframe_columns(raw, "dept")


def test_prefix_dataframe_columns() -> None:
    df = pd.DataFrame({"id": [1], "name": ["Alice"]})
    prefixed = prefix_dataframe_columns(df, "emp")
    assert list(prefixed.columns) == ["emp__id", "emp__name"]


def test_apply_pre_filter_predicate(engine: PandasExecutionEngine, employees_df: pd.DataFrame) -> None:
    filters = [
        Predicate(
            left="emp.first_name",
            operator="==",
            right="Alice",
            right_type="literal",
        )
    ]
    filtered = engine.apply_pre_filters(employees_df, filters)
    assert len(filtered) == 1
    assert filtered.iloc[0]["emp__first_name"] == "Alice"


def test_apply_pre_filter_expression(engine: PandasExecutionEngine, employees_df: pd.DataFrame) -> None:
    filters = [ExpressionFilter(type="expression", value="emp__department_id == 10")]
    filtered = engine.apply_pre_filters(employees_df, filters)
    assert len(filtered) == 1
    assert filtered.iloc[0]["emp__first_name"] == "Alice"


def test_apply_pre_filter_on_join_table_before_merge(
    engine: PandasExecutionEngine,
    departments_df: pd.DataFrame,
) -> None:
    """Join pre_filters use the same engine method on a prefixed join DataFrame."""
    filters = [
        Predicate(
            left="dept.id",
            operator="==",
            right=20,
            right_type="literal",
        )
    ]
    filtered = engine.apply_pre_filters(departments_df, filters)
    assert len(filtered) == 1
    assert filtered.iloc[0]["dept__name"] == "Sales"


def test_apply_join_left(engine: PandasExecutionEngine, employees_df: pd.DataFrame, departments_df: pd.DataFrame) -> None:
    conditions = [
        Predicate(
            left="emp.department_id",
            operator="==",
            right="dept.id",
            right_type="column",
        )
    ]
    joined = engine.apply_join(employees_df, departments_df, "LEFT", conditions)
    assert len(joined) == 3
    assert "dept__name" in joined.columns
    carol = joined[joined["emp__first_name"] == "Carol"].iloc[0]
    assert carol["dept__name"] == "Marketing"


def test_extract_merge_key_columns() -> None:
    conditions = [
        Predicate(
            left="emp.department_id",
            operator="==",
            right="dept.id",
            right_type="column",
        )
    ]
    left_on, right_on = extract_merge_key_columns(conditions)
    assert left_on == ["emp__department_id"]
    assert right_on == ["dept__id"]


def test_expression_derivation(engine: PandasExecutionEngine, employees_df: pd.DataFrame) -> None:
    derivations = [
        ExpressionDerivation(
            variable_name="name_upper",
            transform_type="EXPRESSION",
            expression="emp.first_name",
        )
    ]
    result = engine.apply_derivations(employees_df, derivations)
    assert "deriv__name_upper" in result.columns


def test_regexp_replace_derivation(engine: PandasExecutionEngine, employees_df: pd.DataFrame) -> None:
    derivations = [
        RegexpReplaceDerivation(
            variable_name="domain",
            transform_type="REGEXP_REPLACE",
            source="emp.email",
            pattern=r"@.*",
            replacement="@company.com",
        )
    ]
    result = engine.apply_derivations(employees_df, derivations)
    assert result.loc[0, "deriv__domain"] == "alice@company.com"


def test_case_derivation(engine: PandasExecutionEngine, employees_df: pd.DataFrame) -> None:
    derivations = [
        CaseDerivation(
            variable_name="status_label",
            transform_type="CASE",
            branches=[
                CaseBranch(
                    when=Predicate(
                        left="emp.department_id",
                        operator="==",
                        right=10,
                        right_type="literal",
                    ),
                    then="ENG",
                )
            ],
            else_value="OTHER",
        )
    ]
    result = engine.apply_derivations(employees_df, derivations)
    assert result.loc[0, "deriv__status_label"] == "ENG"
    assert result.loc[1, "deriv__status_label"] == "OTHER"


def test_apply_direct_mappings(engine: PandasExecutionEngine, employees_df: pd.DataFrame) -> None:
    mappings = [
        Mapping(
            target_column="employee_id",
            source_type="DIRECT",
            source_value="emp.id",
            cast_to="str",
            is_nullable=False,
        ),
        Mapping(
            target_column="email",
            source_type="DIRECT",
            source_value="emp.email",
            cast_to="str",
            is_nullable=True,
        ),
    ]
    result = engine.apply_mappings(employees_df, mappings)
    assert list(result.columns) == ["employee_id", "email"]
    assert len(result) == 3


def test_mapping_default_value(engine: PandasExecutionEngine, employees_df: pd.DataFrame) -> None:
    mappings = [
        Mapping(
            target_column="email",
            source_type="DIRECT",
            source_value="emp.email",
            cast_to="str",
            is_nullable=False,
            default_value="unknown@example.com",
        )
    ]
    result = engine.apply_mappings(employees_df, mappings)
    carol = result.iloc[2]
    assert carol["email"] == "unknown@example.com"


def test_mapping_expression_source(engine: PandasExecutionEngine, employees_df: pd.DataFrame) -> None:
    mappings = [
        Mapping(
            target_column="label",
            source_type="EXPRESSION",
            source_value="emp.department_id * 2",
            cast_to="int64",
            is_nullable=False,
        )
    ]
    result = engine.apply_mappings(employees_df, mappings)
    assert result.loc[0, "label"] == 20


def test_cast_failure_raises(engine: PandasExecutionEngine, employees_df: pd.DataFrame) -> None:
    with pytest.raises(TransformError) as exc_info:
        cast_series(employees_df["emp__first_name"], "int64", column="bad_col")
    assert exc_info.value.gate == "G4"


def test_non_nullable_violation_raises(engine: PandasExecutionEngine, employees_df: pd.DataFrame) -> None:
    mappings = [
        Mapping(
            target_column="email",
            source_type="DIRECT",
            source_value="emp.email",
            cast_to="str",
            is_nullable=False,
        )
    ]
    with pytest.raises(TransformError) as exc_info:
        engine.apply_mappings(employees_df, mappings)
    assert exc_info.value.gate == "G4"


def test_post_filter(engine: PandasExecutionEngine, employees_df: pd.DataFrame) -> None:
    mappings = [
        Mapping(
            target_column="employee_id",
            source_type="DIRECT",
            source_value="emp.id",
            cast_to="str",
            is_nullable=False,
        )
    ]
    mapped = engine.apply_mappings(employees_df, mappings)
    filtered = engine.apply_post_filters(
        mapped,
        [
            ExpressionFilter(type="expression", value="employee_id == '1'"),
        ],
    )
    assert len(filtered) == 1


def test_unsafe_expression_rejected() -> None:
    with pytest.raises(TransformError):
        validate_expression_safety("emp__id.__class__")


def test_evaluate_dataframe_expression(employees_df: pd.DataFrame) -> None:
    series = evaluate_dataframe_expression(
        employees_df,
        "emp.department_id * 2",
        phase="derivations",
    )
    assert series.iloc[0] == 20


def test_join_and_map_end_to_end(
    engine: PandasExecutionEngine,
    employees_df: pd.DataFrame,
    departments_df: pd.DataFrame,
) -> None:
    joined = engine.apply_join(
        employees_df,
        departments_df,
        "LEFT",
        [
            Predicate(
                left="emp.department_id",
                operator="==",
                right="dept.id",
                right_type="column",
            )
        ],
    )
    result = engine.apply_mappings(
        joined,
        [
            Mapping(
                target_column="employee_id",
                source_type="DIRECT",
                source_value="emp.id",
                cast_to="str",
                is_nullable=False,
            ),
            Mapping(
                target_column="department_name",
                source_type="DIRECT",
                source_value="dept.name",
                cast_to="str",
                is_nullable=True,
            ),
        ],
    )
    alice = result.iloc[0]
    assert alice["department_name"] == "Engineering"
