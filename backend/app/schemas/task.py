"""Pydantic schemas for Phase 7 Autonomous Agent Tasks and Human Approvals."""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class AgentTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    goal: str = Field(..., min_length=1)
    conversation_id: Optional[uuid.UUID] = None
    custom_plan: Optional[List[Dict[str, Any]]] = None


class AgentStepResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    step_number: int
    name: str
    description: str
    status: str
    tool_name: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    requires_approval: bool = False
    approval_status: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    execution_time_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AgentTaskResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    goal: str
    status: str
    current_step_index: int
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    steps: List[AgentStepResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StepApprovalRequest(BaseModel):
    approved: bool
    reason: Optional[str] = None
