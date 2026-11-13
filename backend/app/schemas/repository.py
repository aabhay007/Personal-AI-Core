"""Pydantic schemas for Code Repositories and Developer Assistant."""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class CodeRepositoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    owner: str = Field(..., min_length=1, max_length=100)
    repo_name: str = Field(..., min_length=1, max_length=100)
    default_branch: str = Field(default="main", max_length=50)
    token: Optional[str] = Field(None, description="GitHub Personal Access Token (PAT)")


class CodeRepositoryResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    owner: str
    repo_name: str
    default_branch: str
    has_token: bool = False
    is_indexed: bool = False
    file_count: int = 0
    last_indexed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RepositoryFileResponse(BaseModel):
    id: uuid.UUID
    file_path: str
    file_name: str
    extension: str
    size_bytes: int
    line_count: int
    content: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CodeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    file_extension: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=20)


class CodeSearchMatch(BaseModel):
    repository_id: str
    file_path: str
    start_line: int
    end_line: int
    content: str
    similarity_score: float


class CodeSearchResponse(BaseModel):
    query: str
    match_count: int
    results: List[CodeSearchMatch]
