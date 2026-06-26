"""Hydrate session state from existing config JSON."""

from __future__ import annotations

import uuid
from typing import Any

from config_ui.backend.domain.models import (
    BlueprintState,
    JoinState,
    MappingState,
    SessionMetadata,
    SessionState,
    SourceFile,
    TargetFile,
)
from config_ui.backend.validation.csv_parser import default_blueprint_id, suggest_alias
from config_ui.backend.validation.g0 import validate_config_dict


def import_config_to_session(config: dict[str, Any]) -> SessionState:
    """Parse validated config into wizard session state."""
    validate_config_dict(config)

    connection_ref = next(iter(config["connections"]))
    connection = config["connections"][connection_ref]

    sources_map: dict[str, SourceFile] = {}
    targets_map: dict[str, TargetFile] = {}

    for blueprint in config["blueprints"]:
        root = blueprint["sources"]["root_table"]
        _ensure_source(sources_map, root["file_name"], root["alias"])
        for join in blueprint["sources"].get("joins", []):
            _ensure_source(sources_map, join["file_name"], join["alias"])
        target = blueprint["target"]
        _ensure_target(targets_map, target["file_name"])

    metadata = SessionMetadata(
        migration_id=config["migration_id"],
        client_id=config["client_id"],
        version=config["version"],
        connection_ref=connection_ref,
        base_path=connection.get("base_path"),
        target_path=connection.get("target_path"),
        source_count=len(sources_map),
        target_count=len(targets_map),
    )

    session = SessionState(
        session_id=uuid.uuid4().hex,
        metadata=metadata,
        sources=list(sources_map.values()),
        targets=list(targets_map.values()),
    )

    for blueprint in sorted(config["blueprints"], key=lambda item: item["sequence_order"]):
        session.blueprints.append(_import_blueprint(blueprint, session))

    return session


def _ensure_source(sources: dict[str, SourceFile], file_name: str, alias: str) -> None:
    if file_name not in sources:
        sources[file_name] = SourceFile(
            source_id=uuid.uuid4().hex,
            file_name=file_name,
            alias=alias,
            columns=[],
        )


def _ensure_target(targets: dict[str, TargetFile], file_name: str) -> None:
    if file_name not in targets:
        targets[file_name] = TargetFile(
            target_id=uuid.uuid4().hex,
            file_name=file_name,
            headers=[],
        )


def _import_blueprint(blueprint: dict[str, Any], session: SessionState) -> BlueprintState:
    root = blueprint["sources"]["root_table"]
    root_source = _find_source(session, root["file_name"])
    target = _find_target(session, blueprint["target"]["file_name"])

    joins: list[JoinState] = []
    for join in blueprint["sources"].get("joins", []):
        join_source = _find_source(session, join["file_name"])
        joins.append(
            JoinState(
                source_id=join_source.source_id,
                join_type=join["join_type"],
                conditions=join.get("conditions", []),
                pre_filters=join.get("pre_filters", []),
            )
        )

    mappings = [
        MappingState(
            target_column=item["target_column"],
            source_type=item["source_type"],
            source_value=item["source_value"],
            cast_to=item["cast_to"],
            is_nullable=item["is_nullable"],
            default_value=item.get("default_value"),
        )
        for item in blueprint.get("mappings", [])
    ]

    return BlueprintState(
        blueprint_id=blueprint["blueprint_id"],
        sequence_order=blueprint["sequence_order"],
        target_id=target.target_id,
        root_source_id=root_source.source_id,
        joins=joins,
        pre_filters=blueprint.get("pre_filters", []),
        derivations=blueprint.get("derivations", []),
        post_filters=blueprint.get("post_filters", []),
        mappings=mappings,
        comment=blueprint.get("comment"),
    )


def _find_source(session: SessionState, file_name: str) -> SourceFile:
    for source in session.sources:
        if source.file_name == file_name:
            return source
    return SourceFile(source_id=uuid.uuid4().hex, file_name=file_name, alias=suggest_alias(file_name))


def _find_target(session: SessionState, file_name: str) -> TargetFile:
    for target in session.targets:
        if target.file_name == file_name:
            return target
    return TargetFile(target_id=uuid.uuid4().hex, file_name=file_name, headers=[])


def initialize_blueprints(session: SessionState) -> None:
    """Create default blueprints after metadata setup."""
    session.blueprints = []
    for index, target in enumerate(session.targets):
        root_source_id = session.sources[0].source_id if session.sources else ""
        session.blueprints.append(
            BlueprintState(
                blueprint_id=default_blueprint_id(target.file_name, index),
                sequence_order=index + 1,
                target_id=target.target_id,
                root_source_id=root_source_id,
                joins=[],
            )
        )
