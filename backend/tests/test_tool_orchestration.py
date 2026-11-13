"""Integration tests for multi-step Tool Calling and AI Orchestration loop."""
from typing import AsyncGenerator
from unittest.mock import patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.providers.base import LLMStreamChunk, TokenUsage
from app.ai.providers.groq_provider import GroqProvider
from app.models.tool import ToolExecution


@pytest.mark.asyncio
async def test_multi_step_tool_orchestration_loop(
    async_client: AsyncClient,
    db_session: AsyncSession
):
    """Verify orchestrator multi-turn tool calling, SSE events, and audit log persistence."""
    # 1. Register user
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "email": "tool_agent@example.com",
        "password": "Password123!",
        "full_name": "Tool Agent"
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch workspace
    ws_res = await async_client.get("/api/v1/workspaces", headers=headers)
    ws_id = ws_res.json()[0]["id"]

    # 2. Create conversation
    conv_res = await async_client.post("/api/v1/conversations", headers=headers, json={
        "workspace_id": ws_id,
        "title": "Calculator Agent Test",
        "model_provider": "groq",
        "model_name": "qwen/qwen3.8-27b"
    })
    conv_id = conv_res.json()["id"]

    # 3. Simulate a multi-step turn:
    # Call 1: LLM yields a tool call for calculator
    # Call 2: LLM receives result and synthesizes the answer
    call_count = 0

    async def mock_stream(*args, **kwargs) -> AsyncGenerator[LLMStreamChunk, None]:
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            # Yield tool call
            yield LLMStreamChunk(
                tool_calls=[{
                    "index": 0,
                    "id": "call_calc_123",
                    "name": "calculator",
                    "arguments": '{"expression": "125 * 8"}'
                }]
            )
        else:
            # Synthesize final natural language answer
            yield LLMStreamChunk(delta="The answer is ")
            yield LLMStreamChunk(delta="1000.")
            yield LLMStreamChunk(
                finish_reason="stop",
                token_usage=TokenUsage(prompt_tokens=30, completion_tokens=10, total_tokens=40)
            )

    with patch.object(GroqProvider, "stream", side_effect=mock_stream):
        stream_res = await async_client.post(
            "/api/v1/chat/stream",
            headers=headers,
            json={
                "conversation_id": conv_id,
                "prompt": "What is 125 multiplied by 8?",
                "provider": "groq",
                "model": "qwen3.8-27b"
            }
        )
        assert stream_res.status_code == 200
        body = stream_res.text

        # 4. Verify SSE event stream contained all steps
        assert "event: message_start" in body
        assert "event: tool_start" in body
        assert '"tool_name": "calculator"' in body
        assert "event: tool_result" in body
        assert '"result": 1000' in body
        assert "event: content_delta" in body
        assert '"delta": "The answer is "' in body
        assert '"delta": "1000."' in body
        assert "event: message_complete" in body

    # 5. Verify ToolExecution audit log was persisted in database
    query = select(ToolExecution).where(ToolExecution.tool_name == "calculator")
    result = await db_session.execute(query)
    exec_record = result.scalar_one_or_none()

    assert exec_record is not None
    assert exec_record.tool_name == "calculator"
    assert exec_record.execution_status == "success"
    assert "1000" in exec_record.result_summary


@pytest.mark.asyncio
async def test_tools_api_endpoints(async_client: AsyncClient):
    """Verify /api/v1/tools list and direct execution endpoint."""
    # Register & get auth headers
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "email": "tool_api_user@example.com",
        "password": "Password123!",
        "full_name": "API User"
    })
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}

    # 1. List tools
    list_res = await async_client.get("/api/v1/tools", headers=headers)
    assert list_res.status_code == 200
    tools = list_res.json()
    assert any(t["name"] == "calculator" for t in tools)
    assert any(t["name"] == "get_current_datetime" for t in tools)

    # 2. Directly execute calculator tool
    exec_res = await async_client.post(
        "/api/v1/tools/calculator/execute",
        headers=headers,
        json={"arguments": {"expression": "99 * 3"}}
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["success"] is True
    assert exec_data["result"]["result"] == 297
