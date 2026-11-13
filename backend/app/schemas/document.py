"""Document schemas for API responses and status."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    uploaded_by: Optional[uuid.UUID] = None
    filename: str
    mime_type: str
    file_size: int
    processing_status: str
    error_message: Optional[str] = None
    created_at: datetime


class DocumentStatusResponse(BaseModel):
    id: uuid.UUID
    filename: str
    processing_status: str
    error_message: Optional[str] = None
