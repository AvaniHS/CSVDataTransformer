"""Exception handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config_ui.backend.api.schemas.common import ErrorDetailSchema, ErrorResponse
from config_ui.backend.exceptions import ConfigUIError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ConfigUIError)
    async def handle_config_ui_error(_request: Request, exc: ConfigUIError) -> JSONResponse:
        status = _status_for_error(exc)
        body = ErrorResponse(
            error=exc.error,
            message=exc.message,
            gate=exc.gate,
            blueprint_id=exc.blueprint_id,
            details=[ErrorDetailSchema(path=detail.path, message=detail.message) for detail in exc.details],
        )
        return JSONResponse(status_code=status, content=body.model_dump())

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, _exc: Exception) -> JSONResponse:
        body = ErrorResponse(error="internal_error", message="An unexpected error occurred")
        return JSONResponse(status_code=500, content=body.model_dump())


def _status_for_error(exc: ConfigUIError) -> int:
    from config_ui.backend.exceptions import (
        ConfigBuildError,
        G0ValidationError,
        SessionError,
        UploadValidationError,
    )

    if isinstance(exc, SessionError):
        return 404
    if isinstance(exc, UploadValidationError):
        return 422
    if isinstance(exc, (G0ValidationError, ConfigBuildError)):
        return 422
    return 400
