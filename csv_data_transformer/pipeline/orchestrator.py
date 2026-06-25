"""Blueprint sequencing — implemented in Phase 5."""

from __future__ import annotations

from typing import Any

from csv_data_transformer.exceptions import PipelineError


class Orchestrator:
    """Runs all blueprints in sequence_order with fail-first semantics."""

    def run(self, config: dict[str, Any], *, api_mode: bool = False) -> list[str]:
        """Execute all blueprints. Returns list of output file paths."""
        raise PipelineError(
            message="Orchestrator.run not implemented yet (Phase 5)",
            gate="G0",
        )
