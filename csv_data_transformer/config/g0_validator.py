"""G0 semantic validation beyond JSON Schema and Pydantic structure."""

from __future__ import annotations

import re

from csv_data_transformer.config.models import (
    Blueprint,
    CaseDerivation,
    ConditionGroup,
    ExpressionDerivation,
    ExpressionFilter,
    FilterItem,
    JoinConditionItem,
    Mapping,
    PipelineConfig,
    Predicate,
    RegexpReplaceDerivation,
)
from csv_data_transformer.engine.operators import normalize_operator
from csv_data_transformer.exceptions import ConfigValidationError, ErrorDetail

_ALIAS_PATTERN = re.compile(r"^[a-zA-Z_][\w]*$")
_COLUMN_REF_PATTERN = re.compile(r"^([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)$")
_DERIV_REF_PATTERN = re.compile(r"^deriv\.([a-zA-Z_][\w]*)$")
_NULL_OPERATORS = frozenset({"IS_NULL", "IS_NOT_NULL"})


def validate_config_semantics(config: PipelineConfig) -> None:
    """Run G0 semantic rules on a parsed PipelineConfig."""
    if not config.blueprints:
        raise ConfigValidationError(
            message="Config must contain at least one blueprint",
            gate="G0",
            migration_id=config.migration_id,
        )

    _validate_connections(config)
    _validate_blueprints(config)


def collect_required_source_files(config: PipelineConfig) -> set[str]:
    """Return deduplicated source file names referenced across all blueprints."""
    files: set[str] = set()
    for blueprint in config.blueprints:
        files.add(blueprint.sources.root_table.file_name)
        for join in blueprint.sources.joins:
            files.add(join.file_name)
    return files


def collect_output_files(config: PipelineConfig) -> list[str]:
    """Return target file names in blueprint sequence order."""
    ordered = sorted(config.blueprints, key=lambda bp: bp.sequence_order)
    return [bp.target.file_name for bp in ordered]


def _validate_connections(config: PipelineConfig) -> None:
    if not config.connections:
        raise ConfigValidationError(
            message="Config must define at least one connection",
            gate="G0",
            migration_id=config.migration_id,
        )

    for name, connection in config.connections.items():
        if connection.resolved_type != "LOCAL_FILE_DIRECTORY":
            raise ConfigValidationError(
                message=f"Unsupported connection type for '{name}': {connection.type}",
                gate="G0",
                migration_id=config.migration_id,
                details=[ErrorDetail(field=f"connections.{name}.type", message=str(connection.type))],
            )


def _validate_blueprints(config: PipelineConfig) -> None:
    blueprint_ids: set[str] = set()
    sequence_orders: set[int] = set()

    for index, blueprint in enumerate(config.blueprints):
        prefix = f"blueprints[{index}]"
        if blueprint.blueprint_id in blueprint_ids:
            raise ConfigValidationError(
                message=f"Duplicate blueprint_id: {blueprint.blueprint_id}",
                gate="G0",
                migration_id=config.migration_id,
                blueprint_id=blueprint.blueprint_id,
                details=[ErrorDetail(field=f"{prefix}.blueprint_id", message="must be unique")],
            )
        blueprint_ids.add(blueprint.blueprint_id)

        if blueprint.sequence_order in sequence_orders:
            raise ConfigValidationError(
                message=f"Duplicate sequence_order: {blueprint.sequence_order}",
                gate="G0",
                migration_id=config.migration_id,
                blueprint_id=blueprint.blueprint_id,
                details=[ErrorDetail(field=f"{prefix}.sequence_order", message="must be unique")],
            )
        sequence_orders.add(blueprint.sequence_order)

        _validate_blueprint(config, blueprint, prefix)


def _validate_blueprint(config: PipelineConfig, blueprint: Blueprint, prefix: str) -> None:
    _resolve_connection_ref(config, blueprint.sources.root_table.connection_ref, prefix, "sources.root_table")
    _resolve_connection_ref(config, blueprint.target.connection_ref, prefix, "target")

    aliases = _collect_aliases(blueprint)
    if len(aliases) != len(_raw_aliases(blueprint)):
        duplicate = _find_duplicate_alias(blueprint)
        raise ConfigValidationError(
            message=f"Duplicate alias in blueprint '{blueprint.blueprint_id}': {duplicate}",
            gate="G0",
            migration_id=config.migration_id,
            blueprint_id=blueprint.blueprint_id,
            details=[ErrorDetail(field=f"{prefix}.sources", message=f"alias '{duplicate}' is duplicated")],
        )

    for alias in aliases:
        if not _ALIAS_PATTERN.match(alias):
            raise ConfigValidationError(
                message=f"Invalid alias '{alias}' in blueprint '{blueprint.blueprint_id}'",
                gate="G0",
                migration_id=config.migration_id,
                blueprint_id=blueprint.blueprint_id,
            )

    if not blueprint.mappings:
        raise ConfigValidationError(
            message=f"Blueprint '{blueprint.blueprint_id}' must define at least one mapping",
            gate="G0",
            migration_id=config.migration_id,
            blueprint_id=blueprint.blueprint_id,
            details=[ErrorDetail(field=f"{prefix}.mappings", message="cannot be empty")],
        )

    target_columns: set[str] = set()
    for mapping_index, mapping in enumerate(blueprint.mappings):
        if mapping.target_column in target_columns:
            raise ConfigValidationError(
                message=f"Duplicate target_column '{mapping.target_column}' in blueprint '{blueprint.blueprint_id}'",
                gate="G0",
                migration_id=config.migration_id,
                blueprint_id=blueprint.blueprint_id,
                details=[ErrorDetail(field=f"{prefix}.mappings[{mapping_index}].target_column", message="duplicate")],
            )
        target_columns.add(mapping.target_column)
        _validate_mapping(blueprint, mapping, aliases, f"{prefix}.mappings[{mapping_index}]")

    for filter_index, item in enumerate(blueprint.pre_filters):
        _validate_filter_item(item, aliases, f"{prefix}.pre_filters[{filter_index}]")

    for filter_index, item in enumerate(blueprint.post_filters):
        _validate_filter_item(item, aliases, f"{prefix}.post_filters[{filter_index}]")

    derivation_names: set[str] = set()
    for derivation_index, derivation in enumerate(blueprint.derivations):
        if derivation.variable_name in derivation_names:
            raise ConfigValidationError(
                message=f"Duplicate derivation variable_name '{derivation.variable_name}'",
                gate="G0",
                migration_id=config.migration_id,
                blueprint_id=blueprint.blueprint_id,
            )
        derivation_names.add(derivation.variable_name)
        _validate_derivation(derivation, aliases, blueprint, f"{prefix}.derivations[{derivation_index}]")
        aliases_with_deriv = aliases | {"deriv"}
        if isinstance(derivation, ExpressionDerivation):
            _validate_column_references_in_text(
                derivation.expression,
                aliases_with_deriv,
                blueprint,
                f"{prefix}.derivations[{derivation_index}].expression",
            )
        elif isinstance(derivation, RegexpReplaceDerivation):
            _validate_qualified_column_ref(
                derivation.source,
                aliases,
                blueprint,
                f"{prefix}.derivations[{derivation_index}].source",
            )

    for join_index, join in enumerate(blueprint.sources.joins):
        join_prefix = f"{prefix}.sources.joins[{join_index}]"
        _resolve_connection_ref(config, join.connection_ref, prefix, f"joins[{join_index}]")
        if not join.conditions:
            raise ConfigValidationError(
                message=f"Join '{join.alias}' must define at least one condition",
                gate="G0",
                migration_id=config.migration_id,
                blueprint_id=blueprint.blueprint_id,
                details=[ErrorDetail(field=f"{join_prefix}.conditions", message="cannot be empty")],
            )
        for condition_index, condition in enumerate(join.conditions):
            _validate_join_condition(
                condition,
                aliases,
                blueprint,
                f"{join_prefix}.conditions[{condition_index}]",
            )
        for filter_index, item in enumerate(join.pre_filters):
            _validate_filter_item(item, {join.alias}, f"{join_prefix}.pre_filters[{filter_index}]")


def _validate_derivation(
    derivation: object,
    aliases: set[str],
    blueprint: Blueprint,
    field_path: str,
) -> None:
    if isinstance(derivation, CaseDerivation):
        for branch_index, branch in enumerate(derivation.branches):
            _validate_join_condition(
                branch.when,
                aliases,
                blueprint,
                f"{field_path}.branches[{branch_index}].when",
            )


def _validate_mapping(
    blueprint: Blueprint,
    mapping: Mapping,
    aliases: set[str],
    field_path: str,
) -> None:
    if mapping.source_type == "DIRECT":
        _validate_qualified_column_ref(mapping.source_value, aliases, blueprint, f"{field_path}.source_value")
    elif mapping.source_type == "DERIVED":
        if not _DERIV_REF_PATTERN.match(mapping.source_value):
            raise ConfigValidationError(
                message=f"DERIVED mapping must use deriv.{{name}} reference, got '{mapping.source_value}'",
                gate="G0",
                migration_id=None,
                blueprint_id=blueprint.blueprint_id,
                details=[ErrorDetail(field=f"{field_path}.source_value", message="invalid DERIVED reference")],
            )
    elif mapping.source_type == "EXPRESSION":
        _validate_column_references_in_text(
            mapping.source_value,
            aliases | {"deriv"},
            blueprint,
            f"{field_path}.source_value",
        )


def _validate_filter_item(item: FilterItem, aliases: set[str], field_path: str) -> None:
    if isinstance(item, ExpressionFilter):
        return
    if isinstance(item, Predicate):
        _validate_predicate(item, aliases, field_path)
        return
    if isinstance(item, ConditionGroup):
        if not item.conditions:
            raise ConfigValidationError(
                message="Filter group must contain at least one condition",
                gate="G0",
                details=[ErrorDetail(field=field_path, message="empty conditions array")],
            )
        for index, child in enumerate(item.conditions):
            _validate_join_condition(child, aliases, None, f"{field_path}.conditions[{index}]")


def _validate_join_condition(
    item: JoinConditionItem,
    aliases: set[str],
    blueprint: Blueprint | None,
    field_path: str,
) -> None:
    if isinstance(item, Predicate):
        _validate_predicate(item, aliases, field_path)
        return
    if isinstance(item, ConditionGroup):
        if not item.conditions:
            raise ConfigValidationError(
                message="Condition group must contain at least one condition",
                gate="G0",
                blueprint_id=blueprint.blueprint_id if blueprint else None,
                details=[ErrorDetail(field=field_path, message="empty conditions array")],
            )
        for index, child in enumerate(item.conditions):
            _validate_join_condition(child, aliases, blueprint, f"{field_path}.conditions[{index}]")


def _validate_predicate(predicate: Predicate, aliases: set[str], field_path: str) -> None:
    try:
        operator = normalize_operator(predicate.operator)
    except ConfigValidationError as exc:
        exc.details.append(ErrorDetail(field=f"{field_path}.operator", message=str(predicate.operator)))
        raise

    if operator in _NULL_OPERATORS:
        return

    if predicate.right is None:
        raise ConfigValidationError(
            message=f"Operator '{operator}' requires a right-hand value",
            gate="G0",
            details=[ErrorDetail(field=f"{field_path}.right", message="is required")],
        )

    if predicate.right_type is None:
        raise ConfigValidationError(
            message=f"Predicate at '{field_path}' must specify right_type",
            gate="G0",
            details=[ErrorDetail(field=f"{field_path}.right_type", message="is required")],
        )

    if predicate.right_type == "column":
        _validate_qualified_column_ref(predicate.left, aliases, None, f"{field_path}.left")
        if isinstance(predicate.right, str):
            _validate_qualified_column_ref(predicate.right, aliases, None, f"{field_path}.right")
    else:
        _validate_qualified_column_ref(predicate.left, aliases, None, f"{field_path}.left")
        if operator in {"IN", "NOT_IN"} and not isinstance(predicate.right, list):
            raise ConfigValidationError(
                message=f"Operator '{operator}' requires an array literal for right",
                gate="G0",
                details=[ErrorDetail(field=f"{field_path}.right", message="must be an array")],
            )


def _validate_qualified_column_ref(
    reference: str,
    aliases: set[str],
    blueprint: Blueprint | None,
    field_path: str,
) -> None:
    match = _COLUMN_REF_PATTERN.match(reference)
    if not match:
        raise ConfigValidationError(
            message=f"Invalid column reference '{reference}' — expected alias.column",
            gate="G0",
            blueprint_id=blueprint.blueprint_id if blueprint else None,
            details=[ErrorDetail(field=field_path, message="expected alias.column format")],
        )
    alias, _column = match.groups()
    if alias not in aliases and alias != "deriv":
        raise ConfigValidationError(
            message=f"Unknown alias '{alias}' in reference '{reference}'",
            gate="G0",
            blueprint_id=blueprint.blueprint_id if blueprint else None,
            details=[ErrorDetail(field=field_path, message=f"alias '{alias}' is not defined")],
        )


def _validate_column_references_in_text(
    text: str,
    aliases: set[str],
    blueprint: Blueprint | None,
    field_path: str,
) -> None:
    for token in re.findall(r"[a-zA-Z_][\w]*\.[a-zA-Z_][\w]*", text):
        _validate_qualified_column_ref(token, aliases, blueprint, field_path)


def _resolve_connection_ref(
    config: PipelineConfig,
    connection_ref: str,
    prefix: str,
    field_name: str,
) -> None:
    if connection_ref not in config.connections:
        raise ConfigValidationError(
            message=f"Unknown connection_ref '{connection_ref}'",
            gate="G0",
            migration_id=config.migration_id,
            details=[ErrorDetail(field=f"{prefix}.{field_name}.connection_ref", message="not found in connections")],
        )


def _raw_aliases(blueprint: Blueprint) -> list[str]:
    aliases = [blueprint.sources.root_table.alias]
    aliases.extend(join.alias for join in blueprint.sources.joins)
    return aliases


def _collect_aliases(blueprint: Blueprint) -> set[str]:
    return set(_raw_aliases(blueprint))


def _find_duplicate_alias(blueprint: Blueprint) -> str:
    seen: set[str] = set()
    for alias in _raw_aliases(blueprint):
        if alias in seen:
            return alias
        seen.add(alias)
    return ""
