"""Tool for inspecting database schemas and metadata in an authorized workspace."""
import uuid
import logging
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.tools.base import BaseTool
from app.models.integration import Integration
from app.integrations.factory import create_connector_from_model
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


class DatabaseMetadataInspectorInput(BaseModel):
    integration_id: Optional[str] = Field(
        None,
        description="Optional ID of the database integration to inspect. If omitted, uses the workspace's default active database."
    )
    schema_name: Optional[str] = Field(
        "public",
        description="The schema to inspect (e.g. 'public', 'analytics'). For SQLite, this is 'main'."
    )
    workspace_id: Optional[str] = Field(
        None,
        description="Workspace ID to query database integrations within."
    )


class DatabaseMetadataInspectorTool(BaseTool):
    name = "db_metadata_inspector"
    description = (
        "Inspect database structure, listing tables, columns, types, nullability, and primary keys "
        "for an authorized database integration in the current workspace. Does not execute arbitrary queries."
    )
    args_schema = DatabaseMetadataInspectorInput
    timeout_seconds = 10.0

    async def execute(
        self,
        integration_id: Optional[str] = None,
        schema_name: Optional[str] = "public",
        workspace_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        if not workspace_id:
            return {"error": "Workspace context is required to inspect database metadata."}

        try:
            ws_uuid = uuid.UUID(workspace_id)
        except ValueError:
            return {"error": "Invalid workspace UUID."}

        async def _run(session):
            stmt = select(Integration).where(
                Integration.workspace_id == ws_uuid,
                Integration.is_active.is_(True)
            )
            if integration_id:
                try:
                    target_id = uuid.UUID(integration_id)
                    stmt = stmt.where(Integration.id == target_id)
                except ValueError:
                    return {"error": f"Invalid integration ID: '{integration_id}'"}

            result = await session.execute(stmt)
            integration = result.scalars().first()
            if not integration:
                return {
                    "error": "No matching active database integration found for this workspace."
                }

            connector = create_connector_from_model(integration)
            target_schema = "main" if integration.integration_type == "sqlite" else (schema_name or "public")
            tables = await connector.get_tables(schema_name=target_schema)

            # Filter by approved_tables if configured
            if integration.approved_tables:
                approved_set = set(t.lower() for t in integration.approved_tables)
                tables = [t for t in tables if t["table_name"].lower() in approved_set]

            return {
                "integration_id": str(integration.id),
                "integration_name": integration.name,
                "integration_type": integration.integration_type,
                "schema": target_schema,
                "table_count": len(tables),
                "tables": tables
            }

        if db is not None:
            return await _run(db)
        else:
            async with AsyncSessionLocal() as session:
                return await _run(session)
