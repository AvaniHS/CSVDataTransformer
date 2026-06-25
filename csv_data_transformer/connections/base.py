"""Connection model types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResolvedPaths:
    """Resolved input and output directories for a connection."""

    base_path: Path
    target_path: Path
