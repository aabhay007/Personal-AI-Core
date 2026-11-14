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
    def build_system_prompt(
        workspace_name: Optional[str] = None,
        documents: Optional[List[str]] = None,
        repositories: Optional[List[str]] = None,
        integrations: Optional[List[str]] = None,
    ) -> str:
        """Construct a dynamic workspace-grounded system prompt."""
        prompt_parts = [
            "You are the Personal AI Core assistant, a high-performance, helpful, and secure AI developer assistant.",
            "Provide clear, accurate, and structured answers. Format code snippets in markdown with appropriate syntax highlighting.",
            "",
            "### Operating Guidelines & Tool Usage:",
            "1. When the user asks about or references any uploaded documents, specifications, or guides, or asks domain questions that could be answered by their files, you MUST use the `document_search` tool to retrieve semantic excerpts before answering. Explicitly cite the source document name and page number in your response.",
            "2. When the user asks about connected code repositories, use `repo_file_tree`, `repo_code_search`, and `repo_read_file` to inspect code.",
            "3. When the user asks about connected databases, use `db_metadata_inspector` and `db_query_tool` to inspect schemas and run safe read-only queries.",
            "4. For mathematical calculations or current time queries, use `calculator` and `get_current_datetime` respectively."
        ]

        context_items = []
        if workspace_name:
            context_items.append(f"- Active Workspace: {workspace_name}")
        if documents:
            docs_formatted = ", ".join(f"`{d}`" for d in documents)
            context_items.append(f"- Uploaded Documents available in this workspace: {docs_formatted}")
        else:
            context_items.append("- Uploaded Documents in this workspace: None currently uploaded")

        if repositories:
            repos_formatted = ", ".join(f"`{r}`" for r in repositories)
            context_items.append(f"- Connected Code Repositories: {repos_formatted}")

        if integrations:
            ints_formatted = ", ".join(f"`{i}`" for i in integrations)
            context_items.append(f"- Connected Database Integrations: {ints_formatted}")

        if context_items:
            prompt_parts.append("")
            prompt_parts.append("### Current Workspace Resources:")
            prompt_parts.extend(context_items)

        return "\n".join(prompt_parts)

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
