"""Conversation and Message API endpoints."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.api.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.services.conversation_service import ConversationService
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationUpdateRequest,
    ConversationResponse,
    ConversationDetailResponse,
    MessageCreateRequest,
    MessageResponse,
)

router = APIRouter(prefix="/conversations")


@router.get(
    "",
    response_model=List[ConversationResponse],
    status_code=status.HTTP_200_OK,
    summary="List conversations in a workspace"
)
async def list_conversations(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID to list conversations from"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> List[Conversation]:
    """List conversations within a workspace, protected by workspace authorization."""
    return await ConversationService.list_conversations(db, workspace_id, current_user)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation"
)
async def create_conversation(
    req: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> Conversation:
    """Create a new conversation within an authorized workspace."""
    return await ConversationService.create_conversation(db, current_user, req)


@router.get(
    "/{id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation details and messages"
)
async def get_conversation(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> Conversation:
    """Fetch conversation and message history with workspace authorization."""
    return await ConversationService.get_conversation(db, id, current_user)


@router.patch(
    "/{id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update conversation"
)
async def update_conversation(
    id: uuid.UUID,
    req: ConversationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> Conversation:
    """Update conversation title."""
    return await ConversationService.update_conversation(db, id, current_user, req)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete conversation"
)
async def delete_conversation(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> None:
    """Delete conversation and all its messages."""
    await ConversationService.delete_conversation(db, id, current_user)


@router.get(
    "/{id}/messages",
    response_model=List[MessageResponse],
    status_code=status.HTTP_200_OK,
    summary="List messages in conversation"
)
async def list_messages(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> List[Message]:
    """List all messages within an authorized conversation."""
    return await ConversationService.list_messages(db, id, current_user)


@router.post(
    "/{id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add message to conversation"
)
async def add_message(
    id: uuid.UUID,
    req: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> Message:
    """Persist a message to a conversation."""
    return await ConversationService.add_message(db, id, current_user, req)
