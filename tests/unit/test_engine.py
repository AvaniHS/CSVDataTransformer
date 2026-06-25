"""Phase 3 column names, operators, and predicate evaluation tests."""

from __future__ import annotations

import pandas as pd
import pytest

from csv_data_transformer.config.models import ConditionGroup, Predicate
from csv_data_transformer.engine.column_names import (
    from_physical_column,
    parse_derivation_ref,
    parse_qualified_column,
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
    evaluate_join_conditions,
    evaluate_predicate_on_dataframe,
)
from csv_data_transformer.exceptions import ConfigValidationError, TransformError


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "emp__id": [1, 2, 3, 4],
            "emp__status": ["ACTIVE", "INACTIVE", "ACTIVE", None],
            "emp__department_id": [10, 20, 10, 30],
            "emp__name": ["Alice", "Bob", "Carol", "Dave"],
            "dept__id": [10, 20, 10, 40],
            "dept__name": ["Eng", "HR", "Eng", "Finance"],
        }
    )


class TestColumnNames:
    def test_physical_and_config_round_trip(self) -> None:
        assert to_physical_column("emp", "first_name") == "emp__first_name"
        assert to_config_column("emp", "first_name") == "emp.first_name"
        assert from_physical_column("emp__first_name") == ("emp", "first_name")

    def test_derivation_references(self) -> None:
        assert to_derivation_column("formatted_phone") == "deriv__formatted_phone"
        assert parse_derivation_ref("deriv.formatted_phone") == "formatted_phone"
        assert resolve_column_reference("deriv.formatted_phone") == "deriv__formatted_phone"

    def test_resolve_qualified_column(self) -> None:
        assert parse_qualified_column("dept.name") == ("dept", "name")
        assert resolve_column_reference("dept.name") == "dept__name"

    def test_translate_expression(self) -> None:
        expr = "emp.id == dept.id and deriv.total > 0"
        assert translate_expression(expr) == "emp__id == dept__id and deriv__total > 0"

    def test_translate_expression_preserves_literals(self) -> None:
        assert translate_expression("emp.status == 'ACTIVE'") == "emp__status == 'ACTIVE'"

    def test_prefix_source_columns(self) -> None:
        assert prefix_source_columns(["id", "name"], "emp") == ["emp__id", "emp__name"]

    def test_invalid_qualified_reference_raises(self) -> None:
        with pytest.raises(ConfigValidationError):
            parse_qualified_column("not_a_column_ref")

    def test_invalid_physical_name_raises(self) -> None:
        with pytest.raises(ConfigValidationError):
            from_physical_column("no_double_underscore")


class TestScalarOperators:
    @pytest.mark.parametrize(
        ("left", "operator", "right", "expected"),
        [
            (1, "==", 1, True),
            (1, "=", 2, False),
            ("a", "!=", "b", True),
            (3, "<", 5, True),
            (5, "<=", 5, True),
            (7, ">", 5, True),
            (7, ">=", 7, True),
            ("ACTIVE", "IN", ["ACTIVE", "PAID"], True),
            ("DRAFT", "NOT IN", ["ACTIVE", "PAID"], True),
            ("Alice", "LIKE", "A%", True),
            ("Alice", "NOT LIKE", "B%", True),
            (None, "IS NULL", None, True),
            ("x", "IS NOT NULL", None, True),
            (float("nan"), "IS NULL", None, True),
        ],
    )
    def test_evaluate_predicate(self, left, operator, right, expected) -> None:
        assert evaluate_predicate(left, operator, right) is expected

    def test_null_comparison_returns_false(self) -> None:
        assert evaluate_predicate(None, "==", "ACTIVE") is False
        assert evaluate_predicate("ACTIVE", "==", None) is False

    def test_like_null_returns_false(self) -> None:
        assert evaluate_predicate(None, "LIKE", "%") is False

    def test_normalize_operator_aliases(self) -> None:
        assert normalize_operator("=") == "=="
        assert normalize_operator("IS NULL") == "IS_NULL"
        assert normalize_operator("NOT LIKE") == "NOT_LIKE"


class TestDataFramePredicates:
    def test_equality_literal(self, sample_df: pd.DataFrame) -> None:
        predicate = Predicate(
            left="emp.status",
            operator="==",
            right="ACTIVE",
            right_type="literal",
        )
        mask = evaluate_predicate_on_dataframe(sample_df, predicate)
        assert mask.tolist() == [True, False, True, False]

    def test_column_to_column_join_condition(self, sample_df: pd.DataFrame) -> None:
        predicate = Predicate(
            left="emp.department_id",
            operator="==",
            right="dept.id",
            right_type="column",
        )
        mask = evaluate_predicate_on_dataframe(sample_df, predicate)
        assert mask.tolist() == [True, True, True, False]

    def test_in_operator(self, sample_df: pd.DataFrame) -> None:
        predicate = Predicate(
            left="emp.status",
            operator="IN",
            right=["ACTIVE", "INACTIVE"],
            right_type="literal",
        )
        mask = evaluate_predicate_on_dataframe(sample_df, predicate)
        assert mask.tolist() == [True, True, True, False]

    def test_like_operator(self, sample_df: pd.DataFrame) -> None:
        predicate = Predicate(
            left="emp.name",
            operator="LIKE",
            right="C%",
            right_type="literal",
        )
        mask = evaluate_predicate_on_dataframe(sample_df, predicate)
        assert mask.tolist() == [False, False, True, False]

    def test_is_null_operator(self, sample_df: pd.DataFrame) -> None:
        predicate = Predicate(left="emp.status", operator="IS_NULL")
        mask = evaluate_predicate_on_dataframe(sample_df, predicate)
        assert mask.tolist() == [False, False, False, True]

    def test_nested_or_group(self, sample_df: pd.DataFrame) -> None:
        group = ConditionGroup(
            logic="OR",
            conditions=[
                Predicate(
                    left="emp.name",
                    operator="==",
                    right="Alice",
                    right_type="literal",
                ),
                Predicate(
                    left="emp.name",
                    operator="==",
                    right="Bob",
                    right_type="literal",
                ),
            ],
        )
        mask = evaluate_condition_group(sample_df, group)
        assert mask.tolist() == [True, True, False, False]

    def test_nested_and_group(self, sample_df: pd.DataFrame) -> None:
        group = ConditionGroup(
            logic="AND",
            conditions=[
                Predicate(
                    left="emp.status",
                    operator="==",
                    right="ACTIVE",
                    right_type="literal",
                ),
                Predicate(
                    left="emp.department_id",
                    operator="==",
                    right=10,
                    right_type="literal",
                ),
            ],
        )
        mask = evaluate_condition_group(sample_df, group)
        assert mask.tolist() == [True, False, True, False]

    def test_top_level_join_conditions_implicit_and(self, sample_df: pd.DataFrame) -> None:
        conditions = [
            Predicate(
                left="emp.status",
                operator="==",
                right="ACTIVE",
                right_type="literal",
            ),
            Predicate(
                left="emp.department_id",
                operator="==",
                right="dept.id",
                right_type="column",
            ),
        ]
        mask = evaluate_join_conditions(sample_df, conditions)
        assert mask.tolist() == [True, False, True, False]

    def test_apply_dataframe_filters_sequential(self, sample_df: pd.DataFrame) -> None:
        filters = [
            Predicate(
                left="emp.status",
                operator="==",
                right="ACTIVE",
                right_type="literal",
            ),
            Predicate(
                left="emp.department_id",
                operator="==",
                right=10,
                right_type="literal",
            ),
        ]
        filtered = apply_dataframe_filters(sample_df, filters)
        assert len(filtered) == 2
        assert filtered["emp__name"].tolist() == ["Alice", "Carol"]

    def test_missing_column_raises_transform_error(self, sample_df: pd.DataFrame) -> None:
        predicate = Predicate(
            left="emp.missing",
            operator="==",
            right="x",
            right_type="literal",
        )
        with pytest.raises(TransformError) as exc_info:
            evaluate_predicate_on_dataframe(sample_df, predicate)
        assert exc_info.value.column == "emp__missing"

    def test_expression_filter(self, sample_df: pd.DataFrame) -> None:
        from csv_data_transformer.config.models import ExpressionFilter
        from csv_data_transformer.engine.predicates import apply_dataframe_filters

        filtered = apply_dataframe_filters(
            sample_df,
            [ExpressionFilter(type="expression", value="emp__id > 2")],
        )
        assert len(filtered) == 2
