"""Config validate/generate/import/export routes."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from config_ui.backend.api.dependencies import get_session_service
from config_ui.backend.api.schemas.common import (
    GenerateRequest,
    GenerateResponse,
    ImportRequest,
    ImportResponse,
    ValidateRequest,
    ValidateResponse,
    session_to_response,
)
from config_ui.backend.domain.session_service import SessionService
from config_ui.backend.validation.g0 import validate_config_dict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["Config"])


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validate config JSON (G0)",
    operation_id="validateConfig",
)
def validate_config(body: ValidateRequest) -> ValidateResponse:
    validate_config_dict(body.config)
    return ValidateResponse()


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Generate config JSON from session",
    operation_id="generateConfig",
)
def generate_config(
    body: GenerateRequest,
    service: SessionService = Depends(get_session_service),
) -> GenerateResponse:
    config = service.generate_config(body.session_id)
    logger.info("Generated config session_id=%s", body.session_id)
    return GenerateResponse(config=config)


@router.post(
    "/import",
    response_model=ImportResponse,
    summary="Import existing config into new session",
    operation_id="importConfig",
)
def import_config(
    body: ImportRequest,
    service: SessionService = Depends(get_session_service),
) -> ImportResponse:
    session = service.import_config(body.config)
    logger.info("Imported config session_id=%s", session.session_id)
    return ImportResponse(session=session_to_response(session))


@router.get(
    "/export",
    summary="Download generated config JSON",
    operation_id="exportConfig",
)
def export_config(
    session_id: str = Query(..., description="Session id"),
    service: SessionService = Depends(get_session_service),
) -> Response:
    config = service.generate_config(session_id)
    payload = json.dumps(config, indent=2)
    return JSONResponse(
        content=json.loads(payload),
        headers={"Content-Disposition": 'attachment; filename="config.json"'},
    )
