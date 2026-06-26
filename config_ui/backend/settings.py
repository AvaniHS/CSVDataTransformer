"""Application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for config UI backend."""

    log_level: str
    workspace_root: Path
    max_upload_mb: int
    cors_origins: list[str]
    schema_path: Path

    @classmethod
    def from_env(cls) -> Settings:
        repo_root = Path(__file__).resolve().parents[2]
        workspace = Path(os.environ.get("CONFIG_UI_WORKSPACE", repo_root / ".config_ui_sessions"))
        cors_raw = os.environ.get("CONFIG_UI_CORS_ORIGINS", "http://localhost:5173")
        return cls(
            log_level=os.environ.get("CONFIG_UI_LOG_LEVEL", "INFO"),
            workspace_root=workspace,
            max_upload_mb=int(os.environ.get("CONFIG_UI_MAX_UPLOAD_MB", "50")),
            cors_origins=[origin.strip() for origin in cors_raw.split(",") if origin.strip()],
            schema_path=repo_root / "schema" / "config.schema.json",
        )
