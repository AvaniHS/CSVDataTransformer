"""Structured logging configuration."""

from __future__ import annotations

import logging
import sys
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(module)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_logging(level: LogLevel | str = "INFO") -> None:
    """Configure root logging once for CLI and API startup."""
    global _configured
    numeric_level = getattr(logging, str(level).upper(), logging.INFO)

    root = logging.getLogger()
    if _configured:
        root.setLevel(numeric_level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)
    _configured = True


def format_context(
    *,
    migration_id: str | None = None,
    client_id: str | None = None,
    blueprint_id: str | None = None,
    gate: str | None = None,
    **extra: str | int | float | bool | None,
) -> str:
    """Build a key=value context suffix for log messages."""
    parts: list[str] = []
    if migration_id:
        parts.append(f"migration_id={migration_id}")
    if client_id:
        parts.append(f"client_id={client_id}")
    if blueprint_id:
        parts.append(f"blueprint_id={blueprint_id}")
    if gate:
        parts.append(f"gate={gate}")
    for key, value in extra.items():
        if value is not None:
            parts.append(f"{key}={value}")
    return " ".join(parts)
