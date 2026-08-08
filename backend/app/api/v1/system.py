"""System status endpoints."""

from fastapi import APIRouter, Request

from app.config import get_settings
from app.schemas.common import ApiResponse, MetricsData

router = APIRouter()


@router.get("/metrics", response_model=ApiResponse[MetricsData])
async def metrics(request: Request) -> ApiResponse[MetricsData]:
    """Return a minimal application metric surface for health monitoring."""
    settings = get_settings()
    return ApiResponse(
        request_id=request.state.request_id,
        data=MetricsData(service=settings.app_name, status="ok"),
    )

