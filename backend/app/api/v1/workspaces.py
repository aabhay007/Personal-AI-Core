"""Workspace management API endpoints."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.api.deps import get_current_user, verify_workspace_access
from app.models.user import User
from app.models.workspace import Workspace
from app.services.workspace_service import WorkspaceService
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceResponse

router = APIRouter(prefix="/workspaces")


@router.get(
    "",
    response_model=List[WorkspaceResponse],
    status_code=status.HTTP_200_OK,
    summary="List workspaces"
)
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> List[Workspace]:
    """List all workspaces that the current user belongs to."""
    return await WorkspaceService.list_user_workspaces(db, current_user)


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workspace"
)
async def create_workspace(
    req: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> Workspace:
    """Create a new workspace owned by the current user."""
    return await WorkspaceService.create_workspace(db, current_user, req)


@router.get(
    "/{id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workspace by ID"
)
async def get_workspace(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> Workspace:
    """Get workspace details if authorized."""
    member = await verify_workspace_access(id, current_user, db)
    return member.workspace
