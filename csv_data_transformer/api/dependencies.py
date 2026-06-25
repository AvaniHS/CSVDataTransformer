"""Shared FastAPI dependencies."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ApiSettings:
    host: str = "0.0.0.0"
    port: int = 8001
    max_body_mb: int = 500
    timeout_sec: int = 300
    log_level: str = "INFO"


def get_settings() -> ApiSettings:
    """Load API settings from environment variables."""
    return ApiSettings(
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8001")),
        max_body_mb=int(os.getenv("API_MAX_BODY_MB", "500")),
        timeout_sec=int(os.getenv("API_TIMEOUT_SEC", "300")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
