"""Single-blueprint ETL flow."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from csv_data_transformer.audit.logger import format_context
from csv_data_transformer.config.models import Blueprint, PipelineConfig
from csv_data_transformer.engine.casting import verify_nullable_column
from csv_data_transformer.engine.pandas_engine import PandasExecutionEngine, prefix_dataframe_columns
from csv_data_transformer.exceptions import TransformError
from csv_data_transformer.io.file_guards import assert_target_empty, file_size_mb
from csv_data_transformer.io.readers.factory import DataReaderFactory
from csv_data_transformer.io.writers.factory import DataTargetFactory
from csv_data_transformer.pipeline.write_verification import verify_post_write

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BlueprintRunResult:
    """Result metadata for a completed blueprint run."""

    blueprint_id: str
    target_file_name: str
    output_path: Path
    row_count: int
    bytes_written: int


class BlueprintRunner:
    """Executes one blueprint through the full pipeline step order."""

    def run(
        self,
        blueprint: Blueprint,
        config: PipelineConfig,
        *,
        input_dir: Path,
        output_dir: Path,
        dry_run: bool = False,
    ) -> BlueprintRunResult:
        """Run blueprint and return output metadata."""
        engine = PandasExecutionEngine(blueprint_id=blueprint.blueprint_id)
        root_table = blueprint.sources.root_table
        root_connection = config.connections[root_table.connection_ref]
        target_connection = config.connections[blueprint.target.connection_ref]

        reader = DataReaderFactory.create(root_connection.file_options.format)
        root_path = input_dir / root_table.file_name
        df = reader.read(root_path, root_connection.file_options)
        df = prefix_dataframe_columns(df, root_table.alias)

        if df.empty:
            raise TransformError(
                message=f"Root extract produced zero rows for '{root_table.file_name}'",
                gate="G2",
                phase="extract",
                blueprint_id=blueprint.blueprint_id,
                migration_id=config.migration_id,
            )

        logger.info(
            "Extracted root file %s",
            format_context(
                migration_id=config.migration_id,
                blueprint_id=blueprint.blueprint_id,
                gate="G2",
                file_name=root_table.file_name,
                rows=len(df),
                size_mb=f"{file_size_mb(root_path):.4f}",
            ),
        )

        df = engine.apply_pre_filters(df, blueprint.pre_filters)

        for join in blueprint.sources.joins:
            join_connection = config.connections[join.connection_ref]
            join_reader = DataReaderFactory.create(join_connection.file_options.format)
            join_path = input_dir / join.file_name
            right_df = join_reader.read(join_path, join_connection.file_options)
            right_df = prefix_dataframe_columns(right_df, join.alias)
            if join.pre_filters:
                rows_before = len(right_df)
                right_df = engine.apply_pre_filters(right_df, join.pre_filters)
                logger.info(
                    "Applied join pre-filters %s",
                    format_context(
                        migration_id=config.migration_id,
                        blueprint_id=blueprint.blueprint_id,
                        gate="G2",
                        join_alias=join.alias,
                        rows_before=rows_before,
                        rows_after=len(right_df),
                    ),
                )
            rows_before = len(df)
            df = engine.apply_join(df, right_df, join.join_type, join.conditions)
            logger.info(
                "Completed join %s",
                format_context(
                    migration_id=config.migration_id,
                    blueprint_id=blueprint.blueprint_id,
                    gate="G2",
                    join_alias=join.alias,
                    join_type=join.join_type,
                    rows_before=rows_before,
                    rows_after=len(df),
                ),
            )

        df = engine.apply_derivations(df, blueprint.derivations)
        target_df = engine.apply_mappings(df, blueprint.mappings)
        target_df = engine.apply_post_filters(target_df, blueprint.post_filters)

        for mapping in blueprint.mappings:
            verify_nullable_column(
                target_df[mapping.target_column],
                column=mapping.target_column,
                is_nullable=mapping.is_nullable,
                blueprint_id=blueprint.blueprint_id,
            )

        logger.info(
            "Pre-write verification passed %s",
            format_context(
                migration_id=config.migration_id,
                blueprint_id=blueprint.blueprint_id,
                gate="G4",
                rows=len(target_df),
                columns=len(target_df.columns),
            ),
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / blueprint.target.file_name

        if dry_run:
            logger.info(
                "Dry-run skipping target write %s",
                format_context(
                    migration_id=config.migration_id,
                    blueprint_id=blueprint.blueprint_id,
                    gate="G4",
                    target_file=target_path.name,
                    rows=len(target_df),
                ),
            )
            return BlueprintRunResult(
                blueprint_id=blueprint.blueprint_id,
                target_file_name=blueprint.target.file_name,
                output_path=target_path,
                row_count=len(target_df),
                bytes_written=0,
            )

        assert_target_empty(target_path, gate="G4")

        writer = DataTargetFactory.create(target_connection.file_options.format)
        bytes_written = writer.write(target_df, target_path, target_connection.file_options)
        verify_post_write(
            target_path,
            expected_rows=len(target_df),
            blueprint_id=blueprint.blueprint_id,
        )

        logger.info(
            "Wrote target file %s",
            format_context(
                migration_id=config.migration_id,
                blueprint_id=blueprint.blueprint_id,
                gate="G5",
                target_file=target_path.name,
                rows=len(target_df),
                bytes_written=bytes_written,
            ),
        )

        return BlueprintRunResult(
            blueprint_id=blueprint.blueprint_id,
            target_file_name=blueprint.target.file_name,
            output_path=target_path,
            row_count=len(target_df),
            bytes_written=bytes_written,
        )
