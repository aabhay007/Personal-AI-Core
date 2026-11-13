"""Phase 6: Developer Assistant and Code Repository Indexing tables.

Revision ID: 005_phase6_developer_assistant
Revises: 004_phase5_integrations
Create Date: 2026-11-13 23:26:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005_phase6_developer_assistant"
down_revision: Union[str, None] = "004_phase5_integrations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. code_repositories
    op.create_table(
        "code_repositories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("owner", sa.String(length=100), nullable=False),
        sa.Column("repo_name", sa.String(length=100), nullable=False),
        sa.Column("default_branch", sa.String(length=50), server_default="main", nullable=False),
        sa.Column("encrypted_token", sa.Text(), nullable=True),
        sa.Column("is_indexed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("file_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_code_repositories_workspace_id"), "code_repositories", ["workspace_id"], unique=False)

    # 2. repository_files
    op.create_table(
        "repository_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=50), nullable=False),
        sa.Column("size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("line_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["code_repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_repository_files_repository_id"), "repository_files", ["repository_id"], unique=False)
    op.create_index(op.f("ix_repository_files_workspace_id"), "repository_files", ["workspace_id"], unique=False)

    # 3. repository_chunks
    op.create_table(
        "repository_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["code_repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_repository_chunks_repository_id"), "repository_chunks", ["repository_id"], unique=False)
    op.create_index(op.f("ix_repository_chunks_workspace_id"), "repository_chunks", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_table("repository_chunks")
    op.drop_table("repository_files")
    op.drop_table("code_repositories")
