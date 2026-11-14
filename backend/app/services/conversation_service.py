"""Conversation and Message management service with strict workspace isolation."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundError
from app.core.config import settings
from app.api.deps import verify_workspace_access
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationUpdateRequest,
    MessageCreateRequest,
)


class ConversationService:
    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        user: User,
        req: ConversationCreateRequest
    ) -> Conversation:
        """Create a new conversation within an authorized workspace."""
        # 1. Enforce workspace membership authorization
        await verify_workspace_access(req.workspace_id, user, db)

        # 2. Resolve defaults safely
        provider = req.model_provider or settings.DEFAULT_LLM_PROVIDER
        model = req.model_name or settings.DEFAULT_MODEL_NAME
        if provider == "groq" and model in ("llama-3.3-70b-versatile", "qwen3.8-27b", "qwen-3.8-27b"):
            model = "qwen/qwen3.8-27b"

        # 3. Create conversation
        conv = Conversation(
            workspace_id=req.workspace_id,
            user_id=user.id,
            title=req.title or "New Conversation",
            model_provider=provider,
            model_name=model
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv

    @staticmethod
    async def list_conversations(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user: User
    ) -> List[Conversation]:
        """List all conversations within a workspace after verifying authorization."""
        await verify_workspace_access(workspace_id, user, db)

        query = select(Conversation).where(
            Conversation.workspace_id == workspace_id
        ).order_by(Conversation.updated_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user: User
    ) -> Conversation:
        """Fetch a conversation with its messages and enforce workspace isolation."""
        query = select(Conversation).options(
            selectinload(Conversation.messages)
        ).where(Conversation.id == conversation_id)

        result = await db.execute(query)
        conv = result.scalar_one_or_none()

        if not conv:
            raise NotFoundError("Conversation not found")

        # Enforce workspace access check
        await verify_workspace_access(conv.workspace_id, user, db)
        return conv

    @staticmethod
    async def update_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user: User,
        req: ConversationUpdateRequest
    ) -> Conversation:
        """Update conversation attributes within authorized workspace."""
        conv = await ConversationService.get_conversation(db, conversation_id, user)

        if req.title is not None:
            conv.title = req.title
        if req.model_provider is not None:
            conv.model_provider = req.model_provider
        if req.model_name is not None:
            model = req.model_name
            if conv.model_provider == "groq" and model in ("llama-3.3-70b-versatile", "qwen3.8-27b", "qwen-3.8-27b"):
                model = "qwen/qwen3.8-27b"
            conv.model_name = model

        await db.commit()
        await db.refresh(conv)
        return conv

    @staticmethod
    async def delete_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user: User
    ) -> None:
        """Delete conversation and cascade messages within authorized workspace."""
        conv = await ConversationService.get_conversation(db, conversation_id, user)
        await db.delete(conv)
        await db.commit()

    @staticmethod
    async def add_message(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user: User,
        req: MessageCreateRequest
    ) -> Message:
        """Append a message to a conversation and update conversation timestamp."""
        conv = await ConversationService.get_conversation(db, conversation_id, user)

        message = Message(
            conversation_id=conv.id,
            role=req.role,
            content=req.content
        )
        db.add(message)
        conv.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def list_messages(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user: User
    ) -> List[Message]:
        """Retrieve all messages in a conversation."""
        conv = await ConversationService.get_conversation(db, conversation_id, user)
        query = select(Message).where(
            Message.conversation_id == conv.id
        ).order_by(Message.created_at.asc())

        result = await db.execute(query)
        return list(result.scalars().all())
