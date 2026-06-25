"""Ephemeral per-request workspace manager."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType


@dataclass
class Workspace:
    """Temporary input/output directories for one API request."""

    root: Path
    input_dir: Path
    output_dir: Path

    def cleanup(self) -> None:
        """Remove the workspace directory tree."""
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)


class WorkspaceManager:
    """Creates and cleans up isolated workspaces."""

    def create(self) -> Workspace:
        root = Path(tempfile.mkdtemp(prefix="csv_transformer_"))
        input_dir = root / "input"
        output_dir = root / "output"
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        return Workspace(root=root, input_dir=input_dir, output_dir=output_dir)

    def managed(self) -> _ManagedWorkspace:
        return _ManagedWorkspace(self)


class _ManagedWorkspace:
    """Context manager that always cleans up the workspace."""

    def __init__(self, manager: WorkspaceManager) -> None:
        self._manager = manager
        self.workspace: Workspace | None = None

    def __enter__(self) -> Workspace:
        self.workspace = self._manager.create()
        return self.workspace

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.workspace is not None:
            self.workspace.cleanup()
