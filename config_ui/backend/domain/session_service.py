"""Session lifecycle service."""

from __future__ import annotations

import uuid
from typing import Any

from config_ui.backend.domain.config_builder import build_config
from config_ui.backend.domain.config_importer import import_config_to_session, initialize_blueprints
from config_ui.backend.domain.models import (
    BlueprintState,
    JoinState,
    MappingState,
    SessionMetadata,
    SessionState,
    SourceFile,
    TargetFile,
)
from config_ui.backend.storage.session_store import SessionStore
from config_ui.backend.validation.csv_parser import (
    default_blueprint_id,
    parse_source_csv,
    parse_target_csv,
    suggest_alias,
)
from config_ui.backend.validation.g0 import validate_config_dict


class SessionService:
    """Orchestrates session CRUD and uploads."""

    def __init__(self, store: SessionStore) -> None:
        self._store = store

    def create_session(self, metadata: SessionMetadata | None = None) -> SessionState:
        session = self._store.create()
        if metadata:
            session.metadata = metadata
            self._store.save(session)
        return session

    def get_session(self, session_id: str) -> SessionState:
        return self._store.get(session_id)

    def update_metadata(self, session_id: str, metadata: SessionMetadata) -> SessionState:
        session = self._store.get(session_id)
        session.metadata = metadata
        self._reconcile_blueprints(session)
        return self._store.save(session)

    def upload_source(self, session_id: str, file_name: str, content: bytes) -> SourceFile:
        session = self._store.get(session_id)
        path = self._store.write_upload(session_id, file_name, content)
        columns, sample_rows, row_count = parse_source_csv(
            path.read_bytes(),
            session_id=session_id,
            file_name=file_name,
        )
        source = SourceFile(
            source_id=uuid.uuid4().hex,
            file_name=file_name,
            alias=suggest_alias(file_name),
            columns=columns,
            sample_rows=sample_rows,
            row_count=row_count,
        )
        session.sources = [item for item in session.sources if item.file_name != file_name]
        session.sources.append(source)
        self._reconcile_blueprints(session)
        return self._store.save(session).sources[-1]

    def upload_target(self, session_id: str, file_name: str, content: bytes) -> tuple[TargetFile, str | None]:
        session = self._store.get(session_id)
        parsed = parse_target_csv(content, session_id=session_id, file_name=file_name)
        self._store.write_upload(session_id, file_name, parsed.headers_only_bytes)
        target = TargetFile(target_id=uuid.uuid4().hex, file_name=file_name, headers=parsed.headers)
        session.targets = [item for item in session.targets if item.file_name != file_name]
        session.targets.append(target)
        self._reconcile_blueprints(session)
        self._store.save(session)
        warning = None
        if parsed.data_rows_removed > 0:
            plural = "row" if parsed.data_rows_removed == 1 else "rows"
            warning = (
                f"Target file '{file_name}': {parsed.data_rows_removed} data {plural} removed — "
                "only the header row is kept."
            )
        return target, warning

    def update_source_alias(self, session_id: str, source_id: str, alias: str) -> SourceFile:
        session = self._store.get(session_id)
        for source in session.sources:
            if source.source_id == source_id:
                source.alias = alias
                self._store.save(session)
                return source
        from config_ui.backend.exceptions import SessionError

        raise SessionError(message=f"Source not found: {source_id}", session_id=session_id)

    def update_blueprint(self, session_id: str, blueprint_id: str, payload: BlueprintState) -> BlueprintState:
        session = self._store.get(session_id)
        for index, blueprint in enumerate(session.blueprints):
            if blueprint.blueprint_id == blueprint_id:
                session.blueprints[index] = payload
                return self._store.save(session).blueprints[index]
        session.blueprints.append(payload)
        return self._store.save(session).blueprints[-1]

    def generate_config(self, session_id: str) -> dict[str, Any]:
        session = self._store.get(session_id)
        workspace = self._store.workspace_path(session_id)
        config = build_config(session, workspace)
        validate_config_dict(config)
        return config

    def import_config(self, config: dict[str, Any]) -> SessionState:
        session = import_config_to_session(config)
        self._store.save(session)
        return session

    def _reconcile_blueprints(self, session: SessionState) -> None:
        if not session.targets:
            session.blueprints = []
            return

        existing = {blueprint.target_id: blueprint for blueprint in session.blueprints}
        blueprints: list[BlueprintState] = []
        for index, target in enumerate(session.targets):
            blueprint = existing.get(target.target_id)
            if blueprint is None:
                root_id = session.sources[0].source_id if session.sources else ""
                blueprint = BlueprintState(
                    blueprint_id=default_blueprint_id(target.file_name, index),
                    sequence_order=index + 1,
                    target_id=target.target_id,
                    root_source_id=root_id,
                )
            else:
                blueprint.sequence_order = index + 1
                if not blueprint.root_source_id and session.sources:
                    blueprint.root_source_id = session.sources[0].source_id
            blueprints.append(blueprint)
        session.blueprints = blueprints
