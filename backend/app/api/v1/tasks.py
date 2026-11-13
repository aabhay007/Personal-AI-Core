"""Autonomous Agent Tasks and Multi-Step Execution API endpoints."""
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db_session
from app.api.deps import get_current_user, verify_workspace_access
from app.models.user import User
from app.models.agent_task import AgentTask, AgentStep
from app.ai.agent_runner import AgentTaskRunner
from app.schemas.task import (
    AgentTaskCreate,
    AgentTaskResponse,
    AgentStepResponse,
    StepApprovalRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks")


async def _get_task_with_steps(db: AsyncSession, task_id: uuid.UUID) -> Optional[AgentTask]:
    stmt = (
        select(AgentTask)
        .where(AgentTask.id == task_id)
        .options(selectinload(AgentTask.steps))
    )
    result = await db.execute(stmt)
    return result.scalars().first()


@router.post(
    "",
    response_model=AgentTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and plan an autonomous multi-step task"
)
async def create_task(
    payload: AgentTaskCreate,
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> AgentTaskResponse:
    """Decompose high-level goal into an ordered plan and initialize the task state machine."""
    await verify_workspace_access(workspace_id, current_user, db)

    task = await AgentTaskRunner.create_and_plan_task(
        db=db,
        workspace_id=workspace_id,
        title=payload.title,
        goal=payload.goal,
        user_id=current_user.id,
        conversation_id=payload.conversation_id,
        custom_plan=payload.custom_plan
    )

    full_task = await _get_task_with_steps(db, task.id)
    return full_task


@router.get(
    "",
    response_model=List[AgentTaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List workspace tasks"
)
async def list_tasks(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> List[AgentTaskResponse]:
    """List all autonomous tasks in the workspace with step counts."""
    await verify_workspace_access(workspace_id, current_user, db)

    stmt = (
        select(AgentTask)
        .where(AgentTask.workspace_id == workspace_id)
        .options(selectinload(AgentTask.steps))
        .order_by(AgentTask.created_at.desc())
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return tasks


@router.get(
    "/{task_id}",
    response_model=AgentTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task details and execution history"
)
async def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> AgentTaskResponse:
    """Retrieve full task state, step history, and tool execution logs."""
    task = await _get_task_with_steps(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_workspace_access(task.workspace_id, current_user, db)
    return task


@router.post(
    "/{task_id}/run",
    response_model=AgentTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute or resume an autonomous task"
)
async def run_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> AgentTaskResponse:
    """Execute sequential steps with automatic checkpointing and human-in-the-loop pauses."""
    task = await _get_task_with_steps(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_workspace_access(task.workspace_id, current_user, db)

    await AgentTaskRunner.run_task(db=db, task_id=task_id)
    updated_task = await _get_task_with_steps(db, task_id)
    return updated_task


@router.post(
    "/{task_id}/steps/{step_id}/approve",
    response_model=AgentTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve sensitive step (Human-in-the-Loop)"
)
async def approve_step(
    task_id: uuid.UUID,
    step_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> AgentTaskResponse:
    """Grant approval for a sensitive action and resume execution."""
    task = await _get_task_with_steps(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_workspace_access(task.workspace_id, current_user, db)

    try:
        await AgentTaskRunner.approve_step(
            db=db,
            task_id=task_id,
            step_id=step_id,
            user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    updated_task = await _get_task_with_steps(db, task_id)
    return updated_task


@router.post(
    "/{task_id}/steps/{step_id}/reject",
    response_model=AgentTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject sensitive step (Human-in-the-Loop)"
)
async def reject_step(
    task_id: uuid.UUID,
    step_id: uuid.UUID,
    payload: StepApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> AgentTaskResponse:
    """Reject a sensitive action, safely halting task execution with reasons recorded."""
    task = await _get_task_with_steps(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await verify_workspace_access(task.workspace_id, current_user, db)

    try:
        await AgentTaskRunner.reject_step(
            db=db,
            task_id=task_id,
            step_id=step_id,
            reason=payload.reason or "Rejected by user"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    updated_task = await _get_task_with_steps(db, task_id)
    return updated_task
