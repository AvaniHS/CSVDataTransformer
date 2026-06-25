"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter

from csv_data_transformer.api.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    operation_id="health_check",
)
def health_check() -> HealthResponse:
    """Return liveness status."""
    return HealthResponse(status="ok")
