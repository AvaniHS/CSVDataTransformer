"""LOCAL_FILE_DIRECTORY connection resolver — implemented in Phase 2."""

from __future__ import annotations

from pathlib import Path

from csv_data_transformer.connections.base import ResolvedPaths
from csv_data_transformer.exceptions import FileGuardError


def resolve_local_paths(base_path: str | Path, target_path: str | Path) -> ResolvedPaths:
    """Resolve connection paths to absolute Path objects."""
    raise FileGuardError(
        message="resolve_local_paths not implemented yet (Phase 2)",
        gate="G1",
    )
