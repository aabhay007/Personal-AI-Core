"""Workspace schemas."""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class WorkspaceMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    created_at: datetime


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime
