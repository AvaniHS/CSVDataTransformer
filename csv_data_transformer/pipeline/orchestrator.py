"""Blueprint sequencing with fail-first semantics."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from csv_data_transformer.audit.logger import format_context
from csv_data_transformer.config.models import PipelineConfig
from csv_data_transformer.connections.local_file import LocalFileConnectionResolver
from csv_data_transformer.exceptions import PipelineError
from csv_data_transformer.pipeline.blueprint_runner import BlueprintRunResult, BlueprintRunner
from csv_data_transformer.pipeline.validator import validate_config_schema, validate_preflight_io

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineRunResult:
    """Aggregate result for a full pipeline run."""

    migration_id: str
    blueprint_results: list[BlueprintRunResult]

    @property
    def output_paths(self) -> list[Path]:
        return [result.output_path for result in self.blueprint_results]


class Orchestrator:
    """Runs all blueprints in sequence_order with fail-first semantics."""

    def __init__(self, runner: BlueprintRunner | None = None) -> None:
        self._runner = runner or BlueprintRunner()

    def run(
        self,
        config: dict[str, Any] | PipelineConfig,
        *,
        api_mode: bool = False,
        workspace_root: Path | None = None,
        uploaded_files: set[str] | None = None,
    ) -> PipelineRunResult:
        """Execute all blueprints. Returns metadata for each output file."""
        pipeline_config = validate_config_schema(config)

        logger.info(
            "Config validation passed %s",
            format_context(
                migration_id=pipeline_config.migration_id,
                client_id=pipeline_config.client_id,
                gate="G0",
                blueprint_count=len(pipeline_config.blueprints),
            ),
        )

        if api_mode and workspace_root is None:
            raise PipelineError(
                message="workspace_root is required when api_mode=True",
                gate="G1",
                migration_id=pipeline_config.migration_id,
            )

        workspace = workspace_root.resolve() if workspace_root is not None else None
        if workspace is not None:
            (workspace / "input").mkdir(parents=True, exist_ok=True)
            (workspace / "output").mkdir(parents=True, exist_ok=True)

        validate_preflight_io(
            pipeline_config,
            workspace_root=workspace if api_mode else None,
            uploaded_files=uploaded_files,
        )

        logger.info(
            "Pre-flight I/O validation passed %s",
            format_context(
                migration_id=pipeline_config.migration_id,
                gate="G1",
            ),
        )

        ordered_blueprints = sorted(
            pipeline_config.blueprints,
            key=lambda blueprint: blueprint.sequence_order,
        )
        results: list[BlueprintRunResult] = []

        for blueprint in ordered_blueprints:
            connection = pipeline_config.connections[blueprint.target.connection_ref]
            resolver = LocalFileConnectionResolver.from_connection(
                connection,
                workspace_root=workspace if api_mode else None,
            )
            result = self._runner.run(
                blueprint,
                pipeline_config,
                input_dir=resolver.base_path,
                output_dir=resolver.target_path,
            )
            results.append(result)

        return PipelineRunResult(
            migration_id=pipeline_config.migration_id,
            blueprint_results=results,
        )
