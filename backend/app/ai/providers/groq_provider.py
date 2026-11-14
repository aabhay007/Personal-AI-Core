"""Groq Cloud LLM Provider implementation."""
import logging
from typing import AsyncGenerator, Dict, List, Optional, Any
from groq import AsyncGroq, APIError, RateLimitError, AuthenticationError
from app.ai.providers.base import LLMProvider, LLMResponse, LLMStreamChunk, TokenUsage
from app.core.config import settings

logger = logging.getLogger(__name__)

GROQ_MODEL_ALIASES = {
    "llama-3.3-70b-versatile": "qwen/qwen3.8-27b",
    "qwen3.8-27b": "qwen/qwen3.8-27b",
    "qwen-3.8-27b": "qwen/qwen3.8-27b",
}


class GroqProvider(LLMProvider):
    """LLM Provider targeting Groq high-speed inference (Qwen 3.8, Llama 3.1, Mixtral)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        if not self.api_key:
            logger.warning("GROQ_API_KEY is not configured in settings or environment.")
        self._client: Optional[AsyncGroq] = None

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def default_model(self) -> str:
        return "qwen/qwen3.8-27b"

    def normalize_model(self, model: Optional[str] = None) -> str:
        target = model or self.default_model
        return GROQ_MODEL_ALIASES.get(target, target)

    def _get_client(self) -> AsyncGroq:
        if not self.api_key:
            raise ValueError(
                "Groq API key is missing. Please set GROQ_API_KEY in your backend/.env file."
            )
        if self._client is None:
            self._client = AsyncGroq(api_key=self.api_key)
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
        target_model = self.normalize_model(model)

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
            logger.error(f"Groq authentication error: {e}")
            raise ValueError("Invalid Groq API key.") from e
        except RateLimitError as e:
            logger.error(f"Groq rate limit reached: {e}")
            raise RuntimeError("Groq rate limit exceeded. Please retry in a moment.") from e
        except APIError as e:
            logger.error(f"Groq API error: {e}")
            raise RuntimeError(f"Groq API returned an error: {e.message}") from e

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        client = self._get_client()
        target_model = self.normalize_model(model)

        kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or settings.MAX_TOKENS_PER_REQUEST,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            stream_resp = await client.chat.completions.create(**kwargs)
            async for chunk in stream_resp:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta_content = choice.delta.content or ""
                finish_reason = choice.finish_reason

                tool_calls_data = None
                if getattr(choice.delta, "tool_calls", None):
                    tool_calls_data = []
                    for tc in choice.delta.tool_calls:
                        func_name = tc.function.name if getattr(tc, "function", None) else None
                        func_args = tc.function.arguments if getattr(tc, "function", None) else None
                        tool_calls_data.append({
                            "index": tc.index,
                            "id": getattr(tc, "id", None),
                            "name": func_name,
                            "arguments": func_args,
                        })

                usage = None
                if getattr(chunk, "x_groq", None) and getattr(chunk.x_groq, "usage", None):
                    u = chunk.x_groq.usage
                    usage = TokenUsage(
                        prompt_tokens=getattr(u, "prompt_tokens", 0),
                        completion_tokens=getattr(u, "completion_tokens", 0),
                        total_tokens=getattr(u, "total_tokens", 0)
                    )

                yield LLMStreamChunk(
                    delta=delta_content,
                    finish_reason=finish_reason,
                    token_usage=usage,
                    tool_calls=tool_calls_data
                )
        except AuthenticationError as e:
            logger.error(f"Groq authentication error in stream: {e}")
            raise ValueError("Invalid Groq API key.") from e
        except RateLimitError as e:
            logger.error(f"Groq rate limit in stream: {e}")
            raise RuntimeError("Groq rate limit exceeded.") from e
        except APIError as e:
            logger.error(f"Groq stream error: {e}")
            raise RuntimeError(f"Groq error: {e.message}") from e
