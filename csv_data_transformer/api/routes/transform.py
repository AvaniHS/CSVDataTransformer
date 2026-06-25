"""Transform and validate routes — implemented in Phase 6."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from csv_data_transformer.api.schemas.errors import ErrorResponse
from csv_data_transformer.api.schemas.validate import ValidateResponse

router = APIRouter(tags=["Transform"])


@router.post(
    "/transform",
    summary="Transform CSV files",
    operation_id="transform_csv",
    description="Upload config JSON and source CSV files. Returns one CSV or a ZIP of outputs.",
    responses={
        200: {
            "description": "Transformed CSV file or ZIP archive",
            "content": {"text/csv": {}, "application/zip": {}},
        },
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def transform(
    config: UploadFile = File(..., description="JSON config file (see sampleConfig.json)"),
    files: list[UploadFile] = File(..., description="Source CSV files referenced in config"),
) -> JSONResponse:
    """Transform endpoint — implemented in Phase 6."""
    return JSONResponse(
        status_code=501,
        content=ErrorResponse(
            error="not_implemented",
            message="POST /transform is not implemented yet (Phase 6)",
            gate="G0",
        ).model_dump(),
    )


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validate config and uploaded files",
    operation_id="validate_config",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def validate(
    config: UploadFile = File(..., description="JSON config file"),
    files: list[UploadFile] = File(..., description="Source CSV files referenced in config"),
) -> JSONResponse:
    """Validate endpoint — implemented in Phase 6."""
    return JSONResponse(
        status_code=501,
        content=ErrorResponse(
            error="not_implemented",
            message="POST /validate is not implemented yet (Phase 6)",
            gate="G0",
        ).model_dump(),
    )
