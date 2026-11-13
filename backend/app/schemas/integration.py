"""Pydantic schemas for Database and external integrations."""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class IntegrationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    integration_type: str = Field(default="postgres", max_length=50)
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(default=5432)
    database: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None)
    ssl_mode: str = Field(default="prefer", max_length=50)
    approved_schemas: Optional[List[str]] = None
    approved_tables: Optional[List[str]] = None
    options: Optional[Dict[str, Any]] = None


class IntegrationTestRequest(BaseModel):
    integration_type: str = Field(default="postgres", max_length=50)
    host: Optional[str] = None
    port: Optional[int] = 5432
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_mode: str = "prefer"
    options: Optional[Dict[str, Any]] = None


class IntegrationTestResponse(BaseModel):
    success: bool
    latency_ms: float
    version: Optional[str] = None
    database: Optional[str] = None
    error: Optional[str] = None


class IntegrationResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    integration_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    has_password: bool = False
    ssl_mode: str
    approved_schemas: Optional[List[str]] = None
    approved_tables: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SchemaMetadataResponse(BaseModel):
    integration_id: str
    integration_name: str
    integration_type: str
    schemas: List[str]
    tables: List[Dict[str, Any]]
