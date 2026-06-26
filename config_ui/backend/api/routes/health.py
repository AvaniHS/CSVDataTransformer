"""Health routes."""

from __future__ import annotations

from fastapi import APIRouter

from config_ui.backend.api.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    operation_id="healthCheck",
)
def health_check() -> HealthResponse:
    return HealthResponse()
