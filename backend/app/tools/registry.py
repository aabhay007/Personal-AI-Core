"""Reusable Tool Registry and safe execution engine."""
import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.base import BaseTool
from app.tools.calculator import CalculatorTool
from app.tools.datetime_tool import DateTimeTool
from app.tools.document_search import DocumentSearchTool
from app.tools.db_metadata_inspector import DatabaseMetadataInspectorTool
from app.tools.db_query_tool import DatabaseQueryTool
from app.tools.repo_read_file import RepoReadFileTool
from app.tools.repo_code_search import RepoCodeSearchTool
from app.tools.repo_file_tree import RepoFileTreeTool
from app.models.tool import ToolExecution

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry managing available tools, schema generation, and safe sandboxed execution."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        # Register core native platform tools
        self.register(CalculatorTool())
        self.register(DateTimeTool())
        self.register(DocumentSearchTool())
        self.register(DatabaseMetadataInspectorTool())
        self.register(DatabaseQueryTool())
        self.register(RepoReadFileTool())
        self.register(RepoCodeSearchTool())
        self.register(RepoFileTreeTool())

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance in the registry."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: '{tool.name}'")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Lookup a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """List all currently registered tools."""
        return list(self._tools.values())

    def get_schemas_for_llm(self) -> List[Dict[str, Any]]:
        """Export OpenAI/Groq compatible tool definitions for all registered tools."""
        return [tool.to_openai_tool_schema() for tool in self._tools.values()]

    async def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        workspace_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Safely execute a tool with validation, timeouts, and database audit logging."""
        tool = self.get_tool(name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{name}' is not registered."
            }

        start_time = time.perf_counter()
        execution_status = "success"
        error_message = None
        result = None

        WORKSPACE_AWARE = (
            "document_search",
            "db_metadata_inspector",
            "db_query_tool",
            "repo_read_file",
            "repo_code_search",
            "repo_file_tree"
        )
        # Automatically supply contextual workspace_id if tool expects it and it's missing
        if name in WORKSPACE_AWARE and workspace_id and not arguments.get("workspace_id"):
            arguments["workspace_id"] = str(workspace_id)

        try:
            # 1. Strict Pydantic argument validation
            validated_args = tool.args_schema(**arguments)
            exec_kwargs = validated_args.model_dump()
            if name in WORKSPACE_AWARE:
                exec_kwargs["db"] = db

            # 2. Execute with strict timeout enforcement
            result = await asyncio.wait_for(
                tool.execute(**exec_kwargs),
                timeout=tool.timeout_seconds
            )

        except ValidationError as e:
            execution_status = "failed"
            error_message = f"Invalid arguments for tool '{name}': {str(e)}"
            logger.warning(f"Validation failed for tool '{name}': {e}")
        except asyncio.TimeoutError:
            execution_status = "timeout"
            error_message = f"Tool '{name}' timed out after {tool.timeout_seconds} seconds."
            logger.error(error_message)
        except Exception as e:
            execution_status = "failed"
            error_message = f"Error during tool execution: {str(e)}"
            logger.exception(f"Unexpected error executing tool '{name}'")

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # 3. Record tool execution in database for audit logs
        if db is not None:
            try:
                record = ToolExecution(
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    tool_name=name,
                    input_arguments=arguments,
                    execution_status=execution_status,
                    result_summary=json.dumps(result)[:1000] if result else None,
                    error_message=error_message,
                    execution_time_ms=duration_ms
                )
                db.add(record)
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to persist tool execution audit log: {e}")

        if execution_status != "success":
            return {
                "success": False,
                "error": error_message,
                "execution_time_ms": duration_ms
            }

        return {
            "success": True,
            "result": result,
            "execution_time_ms": duration_ms
        }


# Global tool registry singleton
tool_registry = ToolRegistry()
