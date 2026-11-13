"""Tool schemas for API responses and execution."""
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ToolResponse(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    requires_approval: bool = False
    timeout_seconds: float = 5.0


class ToolExecuteRequest(BaseModel):
    arguments: Dict[str, Any] = {}
    workspace_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ToolExecuteResponse(BaseModel):
    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: int
