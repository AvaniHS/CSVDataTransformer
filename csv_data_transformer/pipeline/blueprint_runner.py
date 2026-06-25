"""Single-blueprint ETL flow — implemented in Phase 5."""

from __future__ import annotations

from typing import Any

from csv_data_transformer.exceptions import PipelineError


class BlueprintRunner:
    """Executes one blueprint through the full pipeline step order."""

    def run(self, blueprint: dict[str, Any], config: dict[str, Any]) -> str:
        """Run blueprint and return output file path."""
        raise PipelineError(
            message="BlueprintRunner.run not implemented yet (Phase 5)",
            gate="G0",
            blueprint_id=blueprint.get("blueprint_id"),
        )
