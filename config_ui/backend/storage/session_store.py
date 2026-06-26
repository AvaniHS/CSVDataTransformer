"""Session file storage."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from config_ui.backend.domain.models import SessionState
from config_ui.backend.exceptions import SessionError, UploadValidationError
from config_ui.backend.settings import Settings

_SAFE_NAME = re.compile(r"^[a-zA-Z0-9._-]+$")


class SessionStore:
    """Filesystem-backed session persistence."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._settings.workspace_root.mkdir(parents=True, exist_ok=True)

    def create(self) -> SessionState:
        session_id = uuid.uuid4().hex
        session = SessionState(session_id=session_id)
        self._save(session)
        return session

    def get(self, session_id: str) -> SessionState:
        self._assert_safe_id(session_id)
        path = self._session_path(session_id) / "state.json"
        if not path.exists():
            raise SessionError(message=f"Session not found: {session_id}", session_id=session_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        return SessionState.model_validate(data)

    def save(self, session: SessionState) -> SessionState:
        self._save(session)
        return session

    def workspace_path(self, session_id: str) -> Path:
        self._assert_safe_id(session_id)
        path = self._session_path(session_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_upload(self, session_id: str, file_name: str, content: bytes) -> Path:
        if not _SAFE_NAME.match(file_name):
            raise UploadValidationError(
                message=f"Invalid file name: {file_name}",
                session_id=session_id,
                file_role="upload",
            )
        max_bytes = self._settings.max_upload_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise UploadValidationError(
                message=f"File '{file_name}' exceeds {self._settings.max_upload_mb} MB limit",
                session_id=session_id,
                file_role="upload",
            )
        dest = self.workspace_path(session_id) / file_name
        dest.write_bytes(content)
        return dest

    def delete(self, session_id: str) -> None:
        self._assert_safe_id(session_id)
        path = self._session_path(session_id)
        if path.exists():
            for child in sorted(path.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
            for child in sorted(path.rglob("*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
            path.rmdir()

    def _save(self, session: SessionState) -> None:
        self._assert_safe_id(session.session_id)
        folder = self._session_path(session.session_id)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "state.json").write_text(session.model_dump_json(indent=2), encoding="utf-8")

    def _session_path(self, session_id: str) -> Path:
        return self._settings.workspace_root / session_id

    @staticmethod
    def _assert_safe_id(session_id: str) -> None:
        if not re.fullmatch(r"[a-f0-9]{32}", session_id):
            raise SessionError(message=f"Invalid session id: {session_id}", session_id=session_id)
