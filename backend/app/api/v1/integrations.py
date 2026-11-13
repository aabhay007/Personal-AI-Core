"""Database Integrations API endpoints."""
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db_session
from app.api.deps import get_current_user, verify_workspace_access
from app.models.user import User
from app.models.integration import Integration
from app.integrations.encryption import encrypt_secret
from app.integrations.factory import create_connector_from_model, create_connector_from_params
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationResponse,
    IntegrationTestRequest,
    IntegrationTestResponse,
    SchemaMetadataResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations")


def _to_response(integration: Integration) -> IntegrationResponse:
    """Helper to convert model to response schema with sensitive passwords masked."""
    return IntegrationResponse(
        id=integration.id,
        workspace_id=integration.workspace_id,
        name=integration.name,
        integration_type=integration.integration_type,
        host=integration.host,
        port=integration.port,
        database=integration.database,
        username=integration.username,
        has_password=bool(integration.encrypted_password),
        ssl_mode=integration.ssl_mode,
        approved_schemas=integration.approved_schemas,
        approved_tables=integration.approved_tables,
        is_active=integration.is_active,
        created_at=integration.created_at,
        updated_at=integration.updated_at
    )


@router.post(
    "/test",
    response_model=IntegrationTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Test unsaved database connection parameters"
)
async def test_unsaved_connection(
    payload: IntegrationTestRequest,
    current_user: User = Depends(get_current_user)
) -> IntegrationTestResponse:
    """Test connectivity using supplied parameters before saving."""
    try:
        connector = create_connector_from_params(
            integration_type=payload.integration_type,
            host=payload.host,
            port=payload.port,
            database=payload.database,
            username=payload.username,
            password=payload.password,
            ssl_mode=payload.ssl_mode,
            options=payload.options
        )
        result = await connector.test_connection()
        return IntegrationTestResponse(**result)
    except Exception as e:
        logger.warning(f"Connection test error: {e}")
        return IntegrationTestResponse(
            success=False,
            latency_ms=0.0,
            database=payload.database,
            error=str(e)
        )


@router.post(
    "",
    response_model=IntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new database integration"
)
async def create_integration(
    payload: IntegrationCreate,
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> IntegrationResponse:
    """Register and save a new database connection integration."""
    await verify_workspace_access(workspace_id, current_user, db)

    encrypted_pw = encrypt_secret(payload.password) if payload.password else None

    integration = Integration(
        workspace_id=workspace_id,
        created_by=current_user.id,
        name=payload.name,
        integration_type=payload.integration_type,
        host=payload.host,
        port=payload.port,
        database=payload.database,
        username=payload.username,
        encrypted_password=encrypted_pw,
        ssl_mode=payload.ssl_mode,
        approved_schemas=payload.approved_schemas,
        approved_tables=payload.approved_tables,
        options=payload.options,
        is_active=True
    )

    db.add(integration)
    await db.commit()
    await db.refresh(integration)

    return _to_response(integration)


@router.get(
    "",
    response_model=List[IntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="List workspace database integrations"
)
async def list_integrations(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> List[IntegrationResponse]:
    """List all database integrations configured for the workspace."""
    await verify_workspace_access(workspace_id, current_user, db)

    stmt = (
        select(Integration)
        .where(Integration.workspace_id == workspace_id, Integration.is_active.is_(True))
        .order_by(Integration.created_at.desc())
    )
    result = await db.execute(stmt)
    integrations = result.scalars().all()

    return [_to_response(i) for i in integrations]


@router.get(
    "/{integration_id}",
    response_model=IntegrationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single integration"
)
async def get_integration(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> IntegrationResponse:
    """Retrieve integration details (credentials masked)."""
    stmt = select(Integration).where(Integration.id == integration_id, Integration.is_active.is_(True))
    result = await db.execute(stmt)
    integration = result.scalars().first()

    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")

    await verify_workspace_access(integration.workspace_id, current_user, db)
    return _to_response(integration)


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an integration"
)
async def delete_integration(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a database integration."""
    stmt = select(Integration).where(Integration.id == integration_id)
    result = await db.execute(stmt)
    integration = result.scalars().first()

    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")

    await verify_workspace_access(integration.workspace_id, current_user, db)

    await db.delete(integration)
    await db.commit()


@router.post(
    "/{integration_id}/test",
    response_model=IntegrationTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Test saved database connection"
)
async def test_saved_connection(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> IntegrationTestResponse:
    """Test connectivity for an existing saved integration."""
    stmt = select(Integration).where(Integration.id == integration_id, Integration.is_active.is_(True))
    result = await db.execute(stmt)
    integration = result.scalars().first()

    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")

    await verify_workspace_access(integration.workspace_id, current_user, db)

    try:
        connector = create_connector_from_model(integration)
        res = await connector.test_connection()
        return IntegrationTestResponse(**res)
    except Exception as e:
        return IntegrationTestResponse(
            success=False,
            latency_ms=0.0,
            database=integration.database,
            error=str(e)
        )


@router.get(
    "/{integration_id}/schemas",
    response_model=SchemaMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect schemas and tables"
)
async def inspect_integration_schemas(
    integration_id: uuid.UUID,
    schema_name: str = "public",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> SchemaMetadataResponse:
    """Retrieve schemas and tables for a database integration."""
    stmt = select(Integration).where(Integration.id == integration_id, Integration.is_active.is_(True))
    result = await db.execute(stmt)
    integration = result.scalars().first()

    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")

    await verify_workspace_access(integration.workspace_id, current_user, db)

    try:
        connector = create_connector_from_model(integration)
        target_schema = "main" if integration.integration_type == "sqlite" else schema_name
        schemas = await connector.get_schemas()
        tables = await connector.get_tables(schema_name=target_schema)

        # Filter by approved_tables if configured
        if integration.approved_tables:
            approved_set = set(t.lower() for t in integration.approved_tables)
            tables = [t for t in tables if t["table_name"].lower() in approved_set]

        return SchemaMetadataResponse(
            integration_id=str(integration.id),
            integration_name=integration.name,
            integration_type=integration.integration_type,
            schemas=schemas,
            tables=tables
        )
    except Exception as e:
        logger.error(f"Failed to inspect integration schemas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to inspect database schema: {str(e)}"
        )
