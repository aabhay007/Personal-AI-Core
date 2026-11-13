"""Official OpenAI Python SDK LLM Provider implementation."""
import logging
from typing import AsyncGenerator, Dict, List, Optional, Any
from openai import AsyncOpenAI, APIError, RateLimitError, AuthenticationError
from app.ai.providers.base import LLMProvider, LLMResponse, LLMStreamChunk, TokenUsage
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """LLM Provider targeting OpenAI (GPT-4o, GPT-4o-mini)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self._client: Optional[AsyncOpenAI] = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return "gpt-4o"

    def _get_client(self) -> AsyncOpenAI:
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is missing. Set OPENAI_API_KEY in backend/.env"
            )
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        client = self._get_client()
        target_model = model or self.default_model

        kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or settings.MAX_TOKENS_PER_REQUEST,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = await client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            usage = None
            if response.usage:
                usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )

            return LLMResponse(
                content=choice.message.content or "",
                model=target_model,
                provider=self.provider_name,
                token_usage=usage,
                finish_reason=choice.finish_reason,
            )
        except AuthenticationError as e:
            raise ValueError("Invalid OpenAI API key.") from e
        except RateLimitError as e:
            raise RuntimeError("OpenAI rate limit exceeded.") from e
        except APIError as e:
            raise RuntimeError(f"OpenAI API error: {e.message}") from e

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        client = self._get_client()
        target_model = model or self.default_model

        kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or settings.MAX_TOKENS_PER_REQUEST,
            "stream": True,
            "stream_options": {"include_usage": True}
        }
        if tools:
            kwargs["tools"] = tools

        try:
            stream_resp = await client.chat.completions.create(**kwargs)
            async for chunk in stream_resp:
                delta_content = ""
                finish_reason = None
                usage = None

                if chunk.choices:
                    choice = chunk.choices[0]
                    delta_content = choice.delta.content or ""
                    finish_reason = choice.finish_reason

                if getattr(chunk, "usage", None):
                    u = chunk.usage
                    usage = TokenUsage(
                        prompt_tokens=getattr(u, "prompt_tokens", 0),
                        completion_tokens=getattr(u, "completion_tokens", 0),
                        total_tokens=getattr(u, "total_tokens", 0)
                    )

                yield LLMStreamChunk(
                    delta=delta_content,
                    finish_reason=finish_reason,
                    token_usage=usage
                )
        except AuthenticationError as e:
            raise ValueError("Invalid OpenAI API key.") from e
        except RateLimitError as e:
            raise RuntimeError("OpenAI rate limit exceeded.") from e
        except APIError as e:
            raise RuntimeError(f"OpenAI error: {e.message}") from e
