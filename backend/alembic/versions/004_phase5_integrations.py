"""Phase 5: Integrations table for external databases and services.

Revision ID: 004_phase5_integrations
Revises: 003_phase4_documents
Create Date: 2026-11-13 23:20:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004_phase5_integrations"
down_revision: Union[str, None] = "003_phase4_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "integrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("integration_type", sa.String(length=50), server_default="postgres", nullable=False),
        sa.Column("host", sa.String(length=255), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("database", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("encrypted_password", sa.Text(), nullable=True),
        sa.Column("ssl_mode", sa.String(length=50), server_default="prefer", nullable=False),
        sa.Column("approved_schemas", sa.JSON(), nullable=True),
        sa.Column("approved_tables", sa.JSON(), nullable=True),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_integrations_workspace_id"), "integrations", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_integrations_workspace_id"), table_name="integrations")
    op.drop_table("integrations")
