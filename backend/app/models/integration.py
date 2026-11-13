"""Integration model for external databases and third-party services."""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    integration_type: Mapped[str] = mapped_column(
        String(50),
        default="postgres",  # "postgres", "sqlite", "sqlserver"
        nullable=False
    )
    host: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    port: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    database: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    encrypted_password: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    ssl_mode: Mapped[str] = mapped_column(
        String(50),
        default="prefer",
        nullable=False
    )
    approved_schemas: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True
    )
    approved_tables: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True
    )
    options: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    workspace = relationship("Workspace")
    creator = relationship("User")
