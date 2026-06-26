"""Assemble engine config JSON from session state."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config_ui.backend.domain.models import BlueprintState, MappingState, SessionState, SourceFile, JoinState
from config_ui.backend.exceptions import ConfigBuildError, ErrorDetail


def build_config(session: SessionState, workspace: Path) -> dict[str, Any]:
    """Build config dict from wizard session."""
    _validate_counts(session)
    base_path, target_path = _resolve_paths(session, workspace)

    sources_by_id = {source.source_id: source for source in session.sources}
    targets_by_id = {target.target_id: target for target in session.targets}

    config: dict[str, Any] = {
        "$schema": "./schema/config.schema.json",
        "migration_id": session.metadata.migration_id,
        "client_id": session.metadata.client_id,
        "version": session.metadata.version,
        "connections": {
            session.metadata.connection_ref: {
                "type": "LOCAL_FILE_DIRECTORY",
                "base_path": base_path,
                "target_path": target_path,
                "file_options": {
                    "format": "CSV",
                    "encoding": "utf-8",
                    "delimiter": ",",
                    "quote_char": '"',
                    "header_row": True,
                    "max_file_size_mb": 100,
                },
            }
        },
        "blueprints": [],
    }

    for blueprint in sorted(session.blueprints, key=lambda item: item.sequence_order):
        config["blueprints"].append(_build_blueprint(blueprint, session, sources_by_id, targets_by_id))

    return config


def _validate_counts(session: SessionState) -> None:
    if len(session.sources) != session.metadata.source_count:
        raise ConfigBuildError(
            message=f"Expected {session.metadata.source_count} source files, got {len(session.sources)}",
            details=[ErrorDetail(message="Upload all source files", path="sources")],
        )
    if len(session.targets) != session.metadata.target_count:
        raise ConfigBuildError(
            message=f"Expected {session.metadata.target_count} target files, got {len(session.targets)}",
            details=[ErrorDetail(message="Upload all target files", path="targets")],
        )
    if len(session.blueprints) != session.metadata.target_count:
        raise ConfigBuildError(
            message="Blueprint count must match target count",
            details=[ErrorDetail(message="Re-initialize session metadata", path="blueprints")],
        )


def _resolve_paths(session: SessionState, workspace: Path) -> tuple[str, str]:
    base = session.metadata.base_path or f"{workspace.as_posix()}/"
    target = session.metadata.target_path or f"{workspace.as_posix()}/output/"
    if not base.endswith("/"):
        base += "/"
    if not target.endswith("/"):
        target += "/"
    return base, target


def _build_blueprint(
    blueprint: BlueprintState,
    session: SessionState,
    sources_by_id: dict[str, SourceFile],
    targets_by_id: dict[str, Any],
) -> dict[str, Any]:
    root = sources_by_id.get(blueprint.root_source_id)
    if root is None:
        raise ConfigBuildError(
            message=f"Blueprint '{blueprint.blueprint_id}' references unknown root source",
            blueprint_id=blueprint.blueprint_id,
            details=[ErrorDetail(message=blueprint.root_source_id, path="root_source_id")],
        )

    target = targets_by_id.get(blueprint.target_id)
    if target is None:
        raise ConfigBuildError(
            message=f"Blueprint '{blueprint.blueprint_id}' references unknown target",
            blueprint_id=blueprint.blueprint_id,
            details=[ErrorDetail(message=blueprint.target_id, path="target_id")],
        )

    joins: list[dict[str, Any]] = []
    for join in blueprint.joins:
        join_source = sources_by_id.get(join.source_id)
        if join_source is None:
            raise ConfigBuildError(
                message=f"Join references unknown source in blueprint '{blueprint.blueprint_id}'",
                blueprint_id=blueprint.blueprint_id,
            )
        joins.append(
            {
                "join_type": join.join_type,
                "connection_ref": session.metadata.connection_ref,
                "file_name": join_source.file_name,
                "alias": join_source.alias,
                "conditions": join.conditions,
                "pre_filters": _resolve_join_pre_filters(blueprint, join),
            }
        )

    mappings = [_build_mapping(mapping) for mapping in blueprint.mappings]
    if not mappings:
        mappings = _default_mappings(blueprint, root, target.headers)

    result: dict[str, Any] = {
        "sequence_order": blueprint.sequence_order,
        "blueprint_id": blueprint.blueprint_id,
        "sources": {
            "root_table": {
                "connection_ref": session.metadata.connection_ref,
                "file_name": root.file_name,
                "alias": root.alias,
            },
            "joins": joins,
        },
        "target": {
            "connection_ref": session.metadata.connection_ref,
            "file_name": target.file_name,
        },
        "pre_filters": blueprint.pre_filters,
        "derivations": blueprint.derivations,
        "mappings": mappings,
        "post_filters": blueprint.post_filters,
    }
    if blueprint.comment:
        result["comment"] = blueprint.comment
    return result


def _resolve_join_pre_filters(blueprint: BlueprintState, join: JoinState) -> list[dict[str, Any]]:
    if join.pre_filters:
        return join.pre_filters
    return blueprint.pending_join_pre_filters.get(join.source_id, [])


def _build_mapping(mapping: MappingState) -> dict[str, Any]:
    item: dict[str, Any] = {
        "target_column": mapping.target_column,
        "source_type": mapping.source_type,
        "source_value": mapping.source_value,
        "cast_to": mapping.cast_to,
        "is_nullable": mapping.is_nullable,
    }
    if mapping.default_value is not None:
        item["default_value"] = mapping.default_value
    return item


def _default_mappings(blueprint: BlueprintState, root: SourceFile, headers: list[str]) -> list[dict[str, Any]]:
    """Best-effort direct mappings when user has not configured mappings yet."""
    mappings: list[dict[str, Any]] = []
    root_columns = {column.name for column in root.columns}
    for header in headers:
        source_value = f"{root.alias}.{header}" if header in root_columns else header
        source_type = "DIRECT" if header in root_columns else "EXPRESSION"
        cast_to = next((col.inferred_cast for col in root.columns if col.name == header), "str")
        mappings.append(
            {
                "target_column": header,
                "source_type": source_type,
                "source_value": source_value,
                "cast_to": cast_to,
                "is_nullable": True,
            }
        )
    return mappings
