"""Tools management and direct execution endpoints."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.api.deps import get_current_user
from app.models.user import User
from app.tools.registry import tool_registry
from app.schemas.tools import ToolResponse, ToolExecuteRequest, ToolExecuteResponse

router = APIRouter(prefix="/tools")


@router.get(
    "",
    response_model=List[ToolResponse],
    status_code=status.HTTP_200_OK,
    summary="List available tools",
    description="Returns all registered platform tools and their JSON schemas."
)
async def list_tools(
    current_user: User = Depends(get_current_user)
) -> List[ToolResponse]:
    """List all registered tools."""
    tools = tool_registry.list_tools()
    return [
        ToolResponse(
            name=t.name,
            description=t.description,
            parameters=t.args_schema.model_json_schema(),
            requires_approval=t.requires_approval,
            timeout_seconds=t.timeout_seconds
        )
        for t in tools
    ]


@router.post(
    "/{name}/execute",
    response_model=ToolExecuteResponse,
    status_code=status.HTTP_200_OK,
    summary="Directly execute a tool",
    description="Execute an authorized tool directly with argument validation."
)
async def execute_tool(
    name: str,
    req: ToolExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> ToolExecuteResponse:
    """Safely execute a tool by name."""
    tool = tool_registry.get_tool(name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{name}' not found."
        )

    ws_id = uuid.UUID(req.workspace_id) if req.workspace_id else None
    conv_id = uuid.UUID(req.conversation_id) if req.conversation_id else None

    result = await tool_registry.execute_tool(
        name=name,
        arguments=req.arguments,
        workspace_id=ws_id,
        conversation_id=conv_id,
        db=db
    )

    return ToolExecuteResponse(
        tool_name=name,
        success=result["success"],
        result=result.get("result"),
        error=result.get("error"),
        execution_time_ms=result.get("execution_time_ms", 0)
    )
