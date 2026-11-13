"""Health check schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    connected: bool
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    project_name: str
    version: str
    environment: str
    timestamp: datetime
    database: DatabaseHealth
