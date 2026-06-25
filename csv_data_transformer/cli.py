"""Command-line interface for local development and testing."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from csv_data_transformer.audit.logger import configure_logging, format_context
from csv_data_transformer.config.factory import ConfigReaderFactory
from csv_data_transformer.config.g0_validator import collect_output_files, collect_required_source_files
from csv_data_transformer.config.models import PipelineConfig
from csv_data_transformer.exceptions import TransformerError
from csv_data_transformer.pipeline.orchestrator import Orchestrator
from csv_data_transformer.pipeline.validator import validate_preflight_io

logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> PipelineConfig:
    """Load and validate a JSON config file from disk."""
    reader = ConfigReaderFactory.create(config_path)
    return reader.read(config_path)


def run_validate_command(config_path: Path) -> int:
    """Run G0 and G1 validation only."""
    config = load_config(config_path)
    validate_preflight_io(config)

    logger.info(
        "Validation passed %s",
        format_context(
            migration_id=config.migration_id,
            gate="G1",
            blueprint_count=len(config.blueprints),
            required_files=len(collect_required_source_files(config)),
            output_files=len(collect_output_files(config)),
        ),
    )
    return 0


def run_transform_command(config_path: Path, *, dry_run: bool = False) -> int:
    """Execute all blueprints against local filesystem paths."""
    config = load_config(config_path)
    result = Orchestrator().run(config, dry_run=dry_run)

    for blueprint_result in result.blueprint_results:
        logger.info(
            "Blueprint completed %s",
            format_context(
                migration_id=result.migration_id,
                blueprint_id=blueprint_result.blueprint_id,
                rows=blueprint_result.row_count,
                bytes_written=blueprint_result.bytes_written,
                dry_run=dry_run,
                target_file=blueprint_result.target_file_name,
            ),
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="csv-data-transformer",
        description="Configuration-driven CSV transformation engine",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Execute transformation pipeline")
    run_parser.add_argument("--config", required=True, help="Path to JSON config file")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute transforms but skip target writes (G4 nullable checks still run)",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate config and pre-flight I/O")
    validate_parser.add_argument("--config", required=True, help="Path to JSON config file")

    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    config_path = Path(args.config).expanduser().resolve()

    try:
        if args.command == "validate":
            return run_validate_command(config_path)
        if args.command == "run":
            return run_transform_command(config_path, dry_run=args.dry_run)
    except TransformerError as exc:
        logger.error(
            "Pipeline failed %s",
            format_context(
                migration_id=getattr(exc, "migration_id", None),
                blueprint_id=exc.blueprint_id,
                gate=exc.gate,
                message=exc.message,
            ),
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
