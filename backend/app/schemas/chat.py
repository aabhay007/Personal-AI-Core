"""Chat and streaming request schemas."""
import uuid
from typing import Optional
from pydantic import BaseModel, Field


class ChatStreamRequest(BaseModel):
    conversation_id: uuid.UUID
    prompt: str = Field(..., min_length=1)
    provider: Optional[str] = None
    model: Optional[str] = None
