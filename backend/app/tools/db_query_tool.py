"""Controlled read-only database query tool enforcing strict parameterization and table allowlists."""
import uuid
import logging
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.tools.base import BaseTool
from app.models.integration import Integration
from app.integrations.factory import create_connector_from_model
from app.integrations.base import validate_identifier
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


class DatabaseQueryInput(BaseModel):
    table_name: str = Field(
        ...,
        description="The approved table name to query (e.g. 'users', 'invoices', 'products')."
    )
    integration_id: Optional[str] = Field(
        None,
        description="Optional ID of the database integration to query. If omitted, uses the workspace default database."
    )
    columns: Optional[List[str]] = Field(
        None,
        description="List of specific column names to retrieve. If omitted, retrieves all columns."
    )
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Key-value equality filters (e.g. {'status': 'active'}). Values are strictly parameterized."
    )
    order_by: Optional[str] = Field(
        None,
        description="Column name to order results by."
    )
    order_desc: bool = Field(
        default=False,
        description="Sort in descending order if True, ascending if False."
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of rows to return (capped at 100)."
    )
    workspace_id: Optional[str] = Field(
        None,
        description="Workspace ID to query database integrations within."
    )


class DatabaseQueryTool(BaseTool):
    name = "db_query_tool"
    description = (
        "Execute a safe, structured read-only query against an approved table in a connected database. "
        "Allows column selection, parameterized filtering, sorting, and pagination (max 100 rows). "
        "Arbitrary SQL statements, mutations, and DROP/ALTER/INSERT commands are strictly prohibited."
    )
    args_schema = DatabaseQueryInput
    timeout_seconds = 10.0

    async def execute(
        self,
        table_name: str,
        integration_id: Optional[str] = None,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        limit: int = 20,
        workspace_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        if not workspace_id:
            return {"error": "Workspace context is required to execute database queries."}

        try:
            ws_uuid = uuid.UUID(workspace_id)
        except ValueError:
            return {"error": "Invalid workspace UUID."}

        # 1. Identifier safety validation before touching the database
        try:
            safe_table = validate_identifier(table_name, "table name")
            if columns:
                for c in columns:
                    validate_identifier(c, "column name")
            if order_by:
                validate_identifier(order_by, "order_by column")
            if filters:
                for k in filters.keys():
                    validate_identifier(k, "filter column")
        except ValueError as val_err:
            return {"error": f"Security restriction: {str(val_err)}"}

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

            # 2. Enforce approved_tables allowlist if configured
            if integration.approved_tables:
                approved_set = set(t.lower() for t in integration.approved_tables)
                if safe_table.lower() not in approved_set:
                    return {
                        "error": f"Access denied: table '{safe_table}' is not in the approved tables list: {integration.approved_tables}"
                    }

            connector = create_connector_from_model(integration)
            target_schema = "main" if integration.integration_type == "sqlite" else "public"

            try:
                query_result = await connector.execute_read_query(
                    table=safe_table,
                    schema_name=target_schema,
                    columns=columns,
                    filters=filters,
                    order_by=order_by,
                    order_desc=order_desc,
                    limit=limit
                )
                query_result["integration_name"] = integration.name
                query_result["integration_id"] = str(integration.id)
                return query_result
            except Exception as e:
                logger.error(f"Error executing read query on {safe_table}: {e}")
                return {
                    "error": f"Failed to execute read query on table '{safe_table}': {str(e)}"
                }

        if db is not None:
            return await _run(db)
        else:
            async with AsyncSessionLocal() as session:
                return await _run(session)
