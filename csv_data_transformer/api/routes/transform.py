"""Transform and validate routes."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, BackgroundTasks, File, UploadFile
from fastapi.responses import Response

from csv_data_transformer.api.responses import (
    build_csv_response,
    build_transform_headers,
    build_zip_response,
    create_zip_archive,
)
from csv_data_transformer.api.schemas.errors import ErrorResponse
from csv_data_transformer.api.schemas.validate import ValidateResponse
from csv_data_transformer.api.uploads import read_config_upload, save_uploaded_files
from csv_data_transformer.api.workspace import Workspace, WorkspaceManager
from csv_data_transformer.config.g0_validator import collect_output_files, collect_required_source_files
from csv_data_transformer.pipeline.orchestrator import Orchestrator
from csv_data_transformer.pipeline.validator import validate_config_schema, validate_preflight_io

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Transform"])


def _schedule_workspace_cleanup(background_tasks: BackgroundTasks, workspace: Workspace) -> None:
    background_tasks.add_task(workspace.cleanup)


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
    background_tasks: BackgroundTasks,
    config: UploadFile = File(..., description="JSON config file (see sampleConfig.json)"),
    files: list[UploadFile] = File(..., description="Source CSV files referenced in config"),
) -> Response:
    """Validate config, run all blueprints, and return transformed output file(s)."""
    start = time.perf_counter()
    workspace_manager = WorkspaceManager()
    workspace = workspace_manager.create()

    try:
        config_data = await read_config_upload(config)
        uploaded_names = await save_uploaded_files(files, workspace.input_dir)

        orchestrator = Orchestrator()
        result = orchestrator.run(
            config_data,
            api_mode=True,
            workspace_root=workspace.root,
            uploaded_files=uploaded_names,
        )

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        headers = build_transform_headers(result, elapsed_ms)
        _schedule_workspace_cleanup(background_tasks, workspace)

        if len(result.blueprint_results) == 1:
            blueprint_result = result.blueprint_results[0]
            logger.info(
                "Transform completed migration_id=%s blueprint_id=%s rows=%s elapsed_ms=%s",
                result.migration_id,
                blueprint_result.blueprint_id,
                blueprint_result.row_count,
                elapsed_ms,
            )
            return build_csv_response(
                blueprint_result.output_path,
                blueprint_result.target_file_name,
                headers,
            )

        zip_path = workspace.root / "transformed_outputs.zip"
        create_zip_archive(result.blueprint_results, zip_path)
        logger.info(
            "Transform completed migration_id=%s blueprint_count=%s elapsed_ms=%s",
            result.migration_id,
            len(result.blueprint_results),
            elapsed_ms,
        )
        return build_zip_response(zip_path, headers)
    except Exception:
        workspace.cleanup()
        raise


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validate config and uploaded files",
    operation_id="validate_config",
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def validate(
    config: UploadFile = File(..., description="JSON config file"),
    files: list[UploadFile] = File(..., description="Source CSV files referenced in config"),
) -> ValidateResponse:
    """Run G0 and G1 validation without executing the transform pipeline."""
    workspace_manager = WorkspaceManager()
    workspace = workspace_manager.create()

    try:
        config_data = await read_config_upload(config)
        uploaded_names = await save_uploaded_files(files, workspace.input_dir)

        pipeline_config = validate_config_schema(config_data)
        validate_preflight_io(
            pipeline_config,
            workspace_root=workspace.root,
            uploaded_files=uploaded_names,
        )

        return ValidateResponse(
            valid=True,
            migration_id=pipeline_config.migration_id,
            blueprint_count=len(pipeline_config.blueprints),
            output_files=collect_output_files(pipeline_config),
            required_files=sorted(collect_required_source_files(pipeline_config)),
            uploaded_files=sorted(uploaded_names),
        )
    finally:
        workspace.cleanup()
