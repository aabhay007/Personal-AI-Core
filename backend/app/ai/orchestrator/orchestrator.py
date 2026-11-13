"""AI Orchestrator managing conversation flow, provider execution, and persistence."""
import logging
import uuid
from typing import AsyncGenerator, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.providers.registry import get_llm_provider
from app.ai.context.manager import ContextManager
from app.ai.streaming.sse import format_sse_event
from app.models.user import User
from app.models.conversation import Message
from app.services.conversation_service import ConversationService
from app.schemas.conversation import MessageCreateRequest
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIOrchestrator:
    @staticmethod
    async def stream_chat_turn(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user: User,
        user_prompt: str,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Execute a full streaming chat turn:
        
        1. Validates workspace authorization and loads conversation.
        2. Persists user prompt to database.
        3. Formats recent conversation history into LLM context.
        4. Invokes LLM provider (Groq / OpenAI) with streaming.
        5. Yields SSE events (message_start, content_delta, message_complete).
        6. Persists final assistant response and token metrics to database.
        """
        try:
            # 1. Fetch conversation and enforce workspace isolation
            conv = await ConversationService.get_conversation(db, conversation_id, user)

            # 2. Persist user message to DB
            user_msg_req = MessageCreateRequest(role="user", content=user_prompt)
            await ConversationService.add_message(db, conversation_id, user, user_msg_req)

            # 3. Reload all messages for context
            messages = await ConversationService.list_messages(db, conversation_id, user)
            context_messages = ContextManager.build_messages_context(messages)

            # 4. Resolve provider and model
            active_provider_name = provider_name or conv.model_provider or settings.DEFAULT_LLM_PROVIDER
            provider = get_llm_provider(active_provider_name)
            active_model = model_name or conv.model_name or provider.default_model

            # Emit message_start event
            yield format_sse_event("message_start", {
                "conversation_id": str(conversation_id),
                "provider": active_provider_name,
                "model": active_model
            })

            # 5. Stream from provider
            accumulated_content = []
            total_tokens = None

            async for chunk in provider.stream(messages=context_messages, model=active_model):
                if chunk.delta:
                    accumulated_content.append(chunk.delta)
                    yield format_sse_event("content_delta", {"delta": chunk.delta})

                if chunk.token_usage:
                    total_tokens = chunk.token_usage.model_dump()

            full_response_text = "".join(accumulated_content)

            # 6. Persist assistant response to DB
            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response_text,
                token_usage=total_tokens,
                created_at=datetime.now(timezone.utc)
            )
            db.add(assistant_msg)
            conv.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(assistant_msg)

            # Emit message_complete event
            yield format_sse_event("message_complete", {
                "message_id": str(assistant_msg.id),
                "conversation_id": str(conversation_id),
                "token_usage": total_tokens
            })

        except Exception as e:
            logger.exception("Error in AI Orchestrator streaming turn")
            yield format_sse_event("error", {"error": str(e)})
