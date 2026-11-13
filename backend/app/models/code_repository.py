"""CodeRepository, RepositoryFile, and RepositoryChunk models for Phase 6 Developer Assistant."""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CodeRepository(Base):
    __tablename__ = "code_repositories"

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
        String(150),
        nullable=False
    )
    owner: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    repo_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    default_branch: Mapped[str] = mapped_column(
        String(50),
        default="main",
        nullable=False
    )
    encrypted_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    is_indexed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    file_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
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
    files = relationship("RepositoryFile", back_populates="repository", cascade="all, delete-orphan")
    chunks = relationship("RepositoryChunk", back_populates="repository", cascade="all, delete-orphan")


class RepositoryFile(Base):
    __tablename__ = "repository_files"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("code_repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    extension: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    size_bytes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    line_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    repository = relationship("CodeRepository", back_populates="files")


class RepositoryChunk(Base):
    __tablename__ = "repository_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("code_repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    start_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    end_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    embedding: Mapped[List[float]] = mapped_column(
        JSON,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    repository = relationship("CodeRepository", back_populates="chunks")
