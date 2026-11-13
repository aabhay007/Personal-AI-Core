"""Unit and integration tests for AI Orchestrator and SSE Streaming."""
from unittest.mock import patch, MagicMock
from typing import AsyncGenerator
import pytest
from httpx import AsyncClient
from app.ai.providers.base import LLMStreamChunk, TokenUsage
from app.ai.providers.registry import get_llm_provider
from app.ai.providers.groq_provider import GroqProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.context.manager import ContextManager
from app.models.conversation import Message


def test_provider_registry_resolution():
    """Verify provider factory correctly resolves registered providers."""
    groq = get_llm_provider("groq")
    assert isinstance(groq, GroqProvider)
    assert groq.provider_name == "groq"

    openai = get_llm_provider("openai")
    assert isinstance(openai, OpenAIProvider)
    assert openai.provider_name == "openai"

    with pytest.raises(ValueError) as exc:
        get_llm_provider("unsupported_provider")
    assert "Unsupported LLM provider" in str(exc.value)


def test_context_manager_truncation():
    """Verify context manager truncates messages to configured window limit."""
    dummy_messages = [
        Message(role="user", content=f"Message {i}") for i in range(30)
    ]
    context = ContextManager.build_messages_context(dummy_messages, max_messages=10)
    # 1 system prompt + 10 recent messages
    assert len(context) == 11
    assert context[0]["role"] == "system"
    assert context[1]["content"] == "Message 20"
    assert context[-1]["content"] == "Message 29"


@pytest.mark.asyncio
async def test_chat_stream_success_and_persistence(async_client: AsyncClient):
    """Verify /api/v1/chat/stream emits SSE events and persists response."""
    # 1. Register user
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "email": "ai_tester@example.com",
        "password": "Password123!",
        "full_name": "AI Tester"
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch workspace
    ws_res = await async_client.get("/api/v1/workspaces", headers=headers)
    ws_id = ws_res.json()[0]["id"]

    # 2. Create conversation
    conv_res = await async_client.post("/api/v1/conversations", headers=headers, json={
        "workspace_id": ws_id,
        "title": "Groq Streaming Test",
        "model_provider": "groq",
        "model_name": "llama-3.3-70b-versatile"
    })
    conv_id = conv_res.json()["id"]

    # 3. Mock provider stream
    async def mock_stream(*args, **kwargs) -> AsyncGenerator[LLMStreamChunk, None]:
        yield LLMStreamChunk(delta="Hello")
        yield LLMStreamChunk(delta=" from")
        yield LLMStreamChunk(
            delta=" Groq!",
            token_usage=TokenUsage(prompt_tokens=15, completion_tokens=5, total_tokens=20)
        )

    with patch.object(GroqProvider, "stream", side_effect=mock_stream):
        stream_res = await async_client.post(
            "/api/v1/chat/stream",
            headers=headers,
            json={
                "conversation_id": conv_id,
                "prompt": "Say hello to Groq!",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile"
            }
        )
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers["content-type"]
        body = stream_res.text

        # Verify SSE event stream structure
        assert "event: message_start" in body
        assert "event: content_delta" in body
        assert '"delta": "Hello"' in body
        assert '"delta": " from"' in body
        assert '"delta": " Groq!"' in body
        assert "event: message_complete" in body

    # 4. Verify messages are persisted in conversation
    conv_details = await async_client.get(f"/api/v1/conversations/{conv_id}", headers=headers)
    assert conv_details.status_code == 200
    messages = conv_details.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Say hello to Groq!"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hello from Groq!"
    assert messages[1]["token_usage"]["total_tokens"] == 20
