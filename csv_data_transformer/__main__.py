"""CLI entry point for local development and testing."""

from __future__ import annotations

import argparse
import logging
import sys

from csv_data_transformer.audit.logger import configure_logging

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments. Full commands implemented in Phase 7."""
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
    run_parser.add_argument("--dry-run", action="store_true", help="Skip target writes")

    validate_parser = subparsers.add_parser("validate", help="Validate config and pre-flight I/O")
    validate_parser.add_argument("--config", required=True, help="Path to JSON config file")

    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    if args.command in {"run", "validate"}:
        logger.error("CLI %s is not implemented yet (Phase 7)", args.command)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
