"""Session routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Query, UploadFile

from config_ui.backend.api.dependencies import get_session_service
from config_ui.backend.api.schemas.common import (
    BlueprintUpdateRequest,
    MetadataUpdateRequest,
    SessionCreateRequest,
    SessionResponse,
    SourceUploadResponse,
    TargetUploadResponse,
    session_to_response,
)
from config_ui.backend.domain.session_service import SessionService
from config_ui.backend.exceptions import UploadValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session", tags=["Session"])


@router.post(
    "",
    response_model=SessionResponse,
    summary="Create session",
    operation_id="createSession",
)
def create_session(
    body: SessionCreateRequest,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    session = service.create_session(body.metadata)
    logger.info("Created session session_id=%s", session.session_id)
    return session_to_response(session)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get session state",
    operation_id="getSession",
)
def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    return session_to_response(service.get_session(session_id))


@router.put(
    "/{session_id}/metadata",
    response_model=SessionResponse,
    summary="Update session metadata",
    operation_id="updateSessionMetadata",
)
def update_metadata(
    session_id: str,
    body: MetadataUpdateRequest,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    session = service.update_metadata(session_id, body.metadata)
    return session_to_response(session)


@router.post(
    "/{session_id}/sources",
    response_model=SourceUploadResponse,
    summary="Upload source CSV",
    operation_id="uploadSource",
)
async def upload_source(
    session_id: str,
    file: UploadFile = File(...),
    service: SessionService = Depends(get_session_service),
) -> SourceUploadResponse:
    if not file.filename:
        raise UploadValidationError(
            message="Source file name is required",
            session_id=session_id,
            file_role="source",
        )
    content = await file.read()
    source = service.upload_source(session_id, file.filename, content)
    logger.info("Uploaded source session_id=%s file=%s", session_id, file.filename)
    return SourceUploadResponse(source=source)


@router.post(
    "/{session_id}/targets",
    response_model=TargetUploadResponse,
    summary="Upload target CSV (headers only; data rows truncated)",
    operation_id="uploadTarget",
)
async def upload_target(
    session_id: str,
    file: UploadFile = File(...),
    service: SessionService = Depends(get_session_service),
) -> TargetUploadResponse:
    if not file.filename:
        raise UploadValidationError(
            message="Target file name is required",
            session_id=session_id,
            file_role="target",
        )
    content = await file.read()
    target, warning = service.upload_target(session_id, file.filename, content)
    logger.info("Uploaded target session_id=%s file=%s", session_id, file.filename)
    return TargetUploadResponse(target=target, warning=warning)


@router.put(
    "/{session_id}/sources/{source_id}",
    response_model=SourceUploadResponse,
    summary="Update source alias",
    operation_id="updateSourceAlias",
)
def update_source_alias(
    session_id: str,
    source_id: str,
    alias: str = Query(..., min_length=1),
    service: SessionService = Depends(get_session_service),
) -> SourceUploadResponse:
    source = service.update_source_alias(session_id, source_id, alias)
    return SourceUploadResponse(source=source)


@router.put(
    "/{session_id}/blueprints/{blueprint_id}",
    response_model=SessionResponse,
    summary="Update blueprint configuration",
    operation_id="updateBlueprint",
)
def update_blueprint(
    session_id: str,
    blueprint_id: str,
    body: BlueprintUpdateRequest,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    service.update_blueprint(session_id, blueprint_id, body.blueprint)
    return session_to_response(service.get_session(session_id))
