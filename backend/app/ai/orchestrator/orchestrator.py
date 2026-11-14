"""AI Orchestrator managing conversation flow, tool execution loops, and persistence."""
import json
import logging
import uuid
from typing import AsyncGenerator, Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.ai.providers.registry import get_llm_provider
from app.ai.context.manager import ContextManager
from app.ai.streaming.sse import format_sse_event
from app.models.user import User
from app.models.conversation import Message
from app.models.document import Document
from app.models.code_repository import CodeRepository
from app.models.integration import Integration
from app.services.conversation_service import ConversationService
from app.schemas.conversation import MessageCreateRequest
from app.tools.registry import tool_registry
from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5


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
        """Execute a full tool-augmented streaming chat turn.
        
        Orchestration loop:
        1. Persists user prompt to database.
        2. Formats conversation context and discovers available tools.
        3. Calls provider; streams content deltas or processes tool calls.
        4. If tools called: yields tool_start/tool_result SSE events, executes safely,
           appends tool results to context, and iterates (up to MAX_TOOL_ITERATIONS).
        5. Persists final assistant response and token usage metrics to database.
        """
        try:
            # 1. Fetch conversation and enforce workspace isolation
            conv = await ConversationService.get_conversation(db, conversation_id, user)

            # Query workspace context resources for grounded system prompt
            doc_stmt = select(Document.filename).where(
                Document.workspace_id == conv.workspace_id,
                Document.processing_status == "completed"
            )
            doc_rows = (await db.execute(doc_stmt)).scalars().all()

            repo_stmt = select(CodeRepository.name).where(
                CodeRepository.workspace_id == conv.workspace_id
            )
            repo_rows = (await db.execute(repo_stmt)).scalars().all()

            int_stmt = select(Integration.name).where(
                Integration.workspace_id == conv.workspace_id
            )
            int_rows = (await db.execute(int_stmt)).scalars().all()

            workspace_name = conv.workspace.name if getattr(conv, "workspace", None) else None
            system_prompt = ContextManager.build_system_prompt(
                workspace_name=workspace_name,
                documents=list(doc_rows),
                repositories=list(repo_rows),
                integrations=list(int_rows)
            )

            # 2. Persist user message to DB
            user_msg_req = MessageCreateRequest(role="user", content=user_prompt)
            await ConversationService.add_message(db, conversation_id, user, user_msg_req)

            # 3. Reload messages for context
            messages = await ConversationService.list_messages(db, conversation_id, user)
            context_messages = ContextManager.build_messages_context(
                messages,
                system_prompt=system_prompt
            )

            # 4. Resolve provider and model
            active_provider_name = provider_name or conv.model_provider or settings.DEFAULT_LLM_PROVIDER
            provider = get_llm_provider(active_provider_name)
            raw_model = model_name or conv.model_name or provider.default_model
            active_model = provider.normalize_model(raw_model) if hasattr(provider, "normalize_model") else raw_model

            # Keep conversation synchronized if active provider or model changed
            if conv.model_provider != active_provider_name or conv.model_name != active_model:
                conv.model_provider = active_provider_name
                conv.model_name = active_model
                await db.commit()

            # Emit message_start event
            yield format_sse_event("message_start", {
                "conversation_id": str(conversation_id),
                "provider": active_provider_name,
                "model": active_model
            })

            # Retrieve available tool schemas for LLM
            available_tool_schemas = tool_registry.get_schemas_for_llm()

            accumulated_content = []
            total_tokens = None

            # 5. Orchestration loop (capped to prevent infinite agent execution)
            for iteration in range(MAX_TOOL_ITERATIONS):
                # Pass tools unless we are on the final iteration
                tools_to_pass = available_tool_schemas if iteration < (MAX_TOOL_ITERATIONS - 1) else None

                current_turn_content = []
                tool_calls_accumulator: Dict[int, Dict[str, Any]] = {}

                async for chunk in provider.stream(
                    messages=context_messages,
                    tools=tools_to_pass,
                    model=active_model
                ):
                    if chunk.delta:
                        current_turn_content.append(chunk.delta)
                        accumulated_content.append(chunk.delta)
                        yield format_sse_event("content_delta", {"delta": chunk.delta})

                    if chunk.tool_calls:
                        for tc in chunk.tool_calls:
                            idx = tc.get("index", 0)
                            if idx not in tool_calls_accumulator:
                                tool_calls_accumulator[idx] = {
                                    "id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                                    "name": tc.get("name") or "",
                                    "arguments": tc.get("arguments") or ""
                                }
                            else:
                                if tc.get("name"):
                                    tool_calls_accumulator[idx]["name"] += tc["name"]
                                if tc.get("arguments"):
                                    tool_calls_accumulator[idx]["arguments"] += tc["arguments"]

                    if chunk.token_usage:
                        total_tokens = chunk.token_usage.model_dump()

                # If the model requested tool calls, execute them and continue the loop
                if tool_calls_accumulator:
                    assistant_tool_calls = []
                    tool_results_to_append = []

                    for idx, tc_info in sorted(tool_calls_accumulator.items()):
                        call_id = tc_info["id"]
                        tool_name = tc_info["name"]
                        raw_args_str = tc_info["arguments"] or "{}"

                        try:
                            parsed_args = json.loads(raw_args_str)
                        except json.JSONDecodeError:
                            parsed_args = {"raw_input": raw_args_str}

                        assistant_tool_calls.append({
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": raw_args_str
                            }
                        })

                        # Yield tool_start event to client
                        yield format_sse_event("tool_start", {
                            "tool_name": tool_name,
                            "arguments": parsed_args
                        })

                        # Execute tool safely via registry with validation and timeouts
                        execution_result = await tool_registry.execute_tool(
                            name=tool_name,
                            arguments=parsed_args,
                            workspace_id=conv.workspace_id,
                            conversation_id=conv.id,
                            db=db
                        )

                        # Yield tool_result event to client
                        yield format_sse_event("tool_result", {
                            "tool_name": tool_name,
                            "result": execution_result
                        })

                        tool_results_to_append.append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": json.dumps(execution_result)
                        })

                    # Append single assistant message with all tool_calls to context
                    context_messages.append({
                        "role": "assistant",
                        "content": "".join(current_turn_content) or None,
                        "tool_calls": assistant_tool_calls
                    })
                    # Append all tool result messages
                    context_messages.extend(tool_results_to_append)

                    # Continue loop to allow LLM to synthesize tool results
                    continue

                # If no tool calls were requested, we have the final assistant response
                break

            full_response_text = "".join(accumulated_content)

            # 6. Persist final assistant response to DB
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
