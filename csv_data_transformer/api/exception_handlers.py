"""Map domain exceptions to JSON error responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from csv_data_transformer.api.schemas.errors import ErrorDetail, ErrorResponse
from csv_data_transformer.exceptions import (
    ConfigValidationError,
    FileGuardError,
    PipelineError,
    TransformError,
    TransformerError,
    WriteVerificationError,
)

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: dict[type[TransformerError], int] = {
    ConfigValidationError: 400,
    FileGuardError: 400,
    TransformError: 422,
    WriteVerificationError: 422,
    PipelineError: 422,
}


def _to_error_response(exc: TransformerError) -> ErrorResponse:
    return ErrorResponse(
        error=exc.error_code,
        message=exc.message,
        gate=exc.gate,
        blueprint_id=exc.blueprint_id,
        details=[ErrorDetail(message=d.message, field=d.field) for d in exc.details],
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers for domain exceptions and unhandled errors."""

    @app.exception_handler(TransformerError)
    async def transformer_error_handler(
        request: Request,
        exc: TransformerError,
    ) -> JSONResponse:
        status = _STATUS_BY_ERROR.get(type(exc), 422)
        logger.error(
            "gate=%s blueprint_id=%s error=%s message=%s",
            exc.gate,
            exc.blueprint_id,
            exc.error_code,
            exc.message,
        )
        return JSONResponse(status_code=status, content=_to_error_response(exc).model_dump())

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="internal_error",
                message="An unexpected internal error occurred",
            ).model_dump(),
        )
