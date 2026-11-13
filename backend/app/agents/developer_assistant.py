"""Specialized Developer Assistant Agent for repository QA, architecture, and code analysis."""
from typing import List
from app.agents.base import BaseAgent


DEVELOPER_ASSISTANT_SYSTEM_PROMPT = """You are Personal AI Core's Developer Assistant, an expert software architect and systems engineer.

Your primary purpose is to assist developers in exploring, understanding, debugging, and explaining codebases.

Core Operating Principles:
1. Ground your answers in real repository evidence.
2. When answering architectural or structural questions, use `repo_file_tree` to observe project layout.
3. When answering questions about specific classes, functions, or business logic, use `repo_code_search` to find relevant definitions, and `repo_read_file` to inspect the exact lines.
4. ALWAYS cite specific file paths and line ranges in your responses (e.g. `[backend/app/main.py#L12-L35]`).
5. Distinguish clearly between what is directly implemented in the codebase versus your own design recommendations.
6. Provide concrete, concise explanations followed by relevant code references.
"""


class DeveloperAssistantAgent(BaseAgent):
    name: str = "developer_assistant"
    description: str = (
        "Specialized software engineering agent capable of codebase exploration, "
        "code search, architecture analysis, and precise source line citations."
    )
    system_prompt: str = DEVELOPER_ASSISTANT_SYSTEM_PROMPT
    allowed_tools: List[str] = [
        "repo_read_file",
        "repo_code_search",
        "repo_file_tree",
        "calculator",
        "datetime",
        "document_search"
    ]
