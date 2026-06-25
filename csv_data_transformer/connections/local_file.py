"""LOCAL_FILE_DIRECTORY connection resolver."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from csv_data_transformer.config.models import Connection, FileOptions
from csv_data_transformer.connections.base import ResolvedPaths
from csv_data_transformer.exceptions import ConfigValidationError, ErrorDetail


@dataclass(frozen=True)
class LocalFileConnectionResolver:
    """Resolves source and target paths for a local file connection."""

    base_path: Path
    target_path: Path
    file_options: FileOptions

    @classmethod
    def from_connection(
        cls,
        connection: Connection,
        *,
        workspace_root: Path | None = None,
    ) -> LocalFileConnectionResolver:
        """Build resolver from config, optionally overriding paths for API workspace mode."""
        if connection.resolved_type != "LOCAL_FILE_DIRECTORY":
            raise ConfigValidationError(
                message=f"Unsupported connection type: {connection.type}",
                gate="G0",
                details=[ErrorDetail(field="connection.type", message=connection.type)],
            )

        if workspace_root is not None:
            base_path = (workspace_root / "input").resolve()
            target_path = (workspace_root / "output").resolve()
        else:
            base_path = Path(connection.base_path).expanduser().resolve()
            target_path = Path(connection.target_path).expanduser().resolve()

        return cls(
            base_path=base_path,
            target_path=target_path,
            file_options=connection.file_options,
        )

    def resolved_paths(self) -> ResolvedPaths:
        """Return base and target directory paths."""
        return ResolvedPaths(base_path=self.base_path, target_path=self.target_path)

    def source_file_path(self, file_name: str) -> Path:
        """Resolve a source CSV path under base_path."""
        return self.base_path / file_name

    def target_file_path(self, file_name: str) -> Path:
        """Resolve a target CSV path under target_path."""
        return self.target_path / file_name

    def ensure_directories(self) -> None:
        """Create input and output directories when missing."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.target_path.mkdir(parents=True, exist_ok=True)


def resolve_local_paths(base_path: str | Path, target_path: str | Path) -> ResolvedPaths:
    """Resolve connection paths to absolute Path objects."""
    return ResolvedPaths(
        base_path=Path(base_path).expanduser().resolve(),
        target_path=Path(target_path).expanduser().resolve(),
    )
