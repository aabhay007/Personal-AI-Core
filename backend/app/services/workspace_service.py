"""Workspace business logic service."""
import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User
from app.schemas.workspace import WorkspaceCreateRequest


class WorkspaceService:
    @staticmethod
    async def create_workspace(
        db: AsyncSession,
        user: User,
        req: WorkspaceCreateRequest
    ) -> Workspace:
        """Create a new workspace and designate the current user as owner."""
        workspace = Workspace(
            name=req.name,
            owner_id=user.id
        )
        db.add(workspace)
        await db.flush()

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner"
        )
        db.add(member)
        await db.commit()
        await db.refresh(workspace)
        return workspace

    @staticmethod
    async def list_user_workspaces(
        db: AsyncSession,
        user: User
    ) -> List[Workspace]:
        """List all workspaces that the user is a member of."""
        query = select(Workspace).join(
            WorkspaceMember,
            WorkspaceMember.workspace_id == Workspace.id
        ).where(
            WorkspaceMember.user_id == user.id
        ).order_by(Workspace.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
