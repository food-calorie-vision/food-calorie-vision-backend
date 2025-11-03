from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Response model for health checks."""

    status: str = "ok"

