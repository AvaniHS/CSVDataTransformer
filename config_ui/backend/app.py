"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config_ui.backend.api.dependencies import get_settings
from config_ui.backend.api.exception_handlers import register_exception_handlers
from config_ui.backend.api.middleware import RequestIdMiddleware
from config_ui.backend.api.routes import config, health, session
from config_ui.backend.logging_config import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="CSV Config Builder API",
        description="Wizard backend for authoring CSV Data Transformer config JSON files.",
        version="0.1.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        openapi_tags=[
            {"name": "Health", "description": "Service health"},
            {"name": "Session", "description": "Wizard session and uploads"},
            {"name": "Config", "description": "Validate, generate, import, export"},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(session.router, prefix="/api/v1")
    app.include_router(config.router, prefix="/api/v1")

    return app


app = create_app()
