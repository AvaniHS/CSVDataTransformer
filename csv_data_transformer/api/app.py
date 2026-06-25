"""FastAPI application factory with OpenAPI / Swagger configuration."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from csv_data_transformer import __version__
from csv_data_transformer.api.dependencies import get_settings
from csv_data_transformer.api.exception_handlers import register_exception_handlers
from csv_data_transformer.api.middleware import RequestIdMiddleware
from csv_data_transformer.api.routes import health, transform
from csv_data_transformer.audit.logger import configure_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="CSV Data Transformer API",
        description="Upload a JSON config and source CSV files; receive transformed CSV output.",
        version=__version__,
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        openapi_tags=[
            {"name": "Health", "description": "Liveness and readiness checks"},
            {"name": "Transform", "description": "CSV transform and validation operations"},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(transform.router, prefix="/api/v1")

    return app


app = create_app()
