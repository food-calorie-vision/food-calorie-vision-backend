from fastapi import APIRouter

from app.api.v1.schemas.health import HealthStatus

router = APIRouter()


@router.get("", response_model=HealthStatus, summary="API health check")
async def health_check() -> HealthStatus:
    """Return a simple status payload confirming the service is alive."""
    return HealthStatus(status="ok")

