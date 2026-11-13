"""Context Management and history truncation for LLM interactions."""
from typing import Dict, List, Optional, Any
from app.models.conversation import Message
from app.core.config import settings

DEFAULT_SYSTEM_PROMPT = (
    "You are the Personal AI Core assistant, a high-performance, helpful, and secure AI developer assistant. "
    "Provide clear, accurate, and structured answers. Format code snippets in markdown with appropriate syntax highlighting."
)


class ContextManager:
    @staticmethod
    def build_messages_context(
        db_messages: List[Message],
        system_prompt: Optional[str] = None,
        max_messages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Format database message records into the LLM chat completion format.
        
        Applies window truncation to keep the most recent messages within the token budget.
        """
        limit = max_messages or settings.MAX_CONTEXT_MESSAGES
        # Keep most recent messages up to the limit
        recent_messages = db_messages[-limit:] if len(db_messages) > limit else db_messages

        formatted: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT}
        ]

        for msg in recent_messages:
            formatted.append({
                "role": msg.role,
                "content": msg.content
            })

        return formatted
