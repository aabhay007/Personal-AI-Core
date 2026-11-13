"""Health check endpoint implementation."""
from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.core.config import settings
from app.db.session import check_database_connection
from app.schemas.health import HealthResponse, DatabaseHealth

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns the status of the service and connected backend resources."
)
async def get_health_status() -> HealthResponse:
    db_connected, db_message = await check_database_connection()

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        database=DatabaseHealth(
            connected=db_connected,
            message="Database reachable" if db_connected else "Database unreachable"
        )
    )
