"""Phase 3: Tools and tool execution tracking tables.

Revision ID: 002_phase3_tools
Revises: 001_phase1_init
Create Date: 2026-11-13 23:02:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_phase3_tools"
down_revision: Union[str, None] = "001_phase1_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tools table
    op.create_table(
        "tools",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("execution_type", sa.String(length=50), server_default="native", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_tools_workspace_id"), "tools", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_tools_name"), "tools", ["name"], unique=False)

    # 2. tool_executions table
    op.create_table(
        "tool_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("input_arguments", sa.JSON(), nullable=False),
        sa.Column("execution_status", sa.String(length=50), server_default="success", nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_tool_executions_workspace_id"), "tool_executions", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_tool_executions_conversation_id"), "tool_executions", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_tool_executions_tool_name"), "tool_executions", ["tool_name"], unique=False)


def downgrade() -> None:
    op.drop_table("tool_executions")
    op.drop_table("tools")
