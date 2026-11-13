"""Abstract LLM Provider interface and response structures."""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional, Any
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMStreamChunk(BaseModel):
    delta: str = ""
    finish_reason: Optional[str] = None
    token_usage: Optional[TokenUsage] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    token_usage: Optional[TokenUsage] = None
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract interface that all model providers (Groq, OpenAI, etc.) must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier (e.g. 'groq', 'openai')."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model identifier."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Generate a complete response from the LLM."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream response chunks from the LLM."""
        pass
