"""Streaming chat API endpoints using Server-Sent Events."""
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatStreamRequest
from app.ai.orchestrator.orchestrator import AIOrchestrator

router = APIRouter(prefix="/chat")


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream conversation response (SSE)",
    description="Streams LLM tokens and execution events via Server-Sent Events (SSE)."
)
async def stream_chat(
    req: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> StreamingResponse:
    """Stream chat completion tokens using Server-Sent Events (SSE)."""
    generator = AIOrchestrator.stream_chat_turn(
        db=db,
        conversation_id=req.conversation_id,
        user=current_user,
        user_prompt=req.prompt,
        provider_name=req.provider,
        model_name=req.model
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
