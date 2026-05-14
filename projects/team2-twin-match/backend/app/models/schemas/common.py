from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Spec-compliant error envelope: `{"detail": "..."}`."""

    detail: str


class HealthResponse(BaseModel):
    status: str  # "healthy" | "unhealthy"
    database: str  # "connected" | "disconnected"
    timestamp: str
