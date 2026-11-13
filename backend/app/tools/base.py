"""Base Tool abstraction and schema definitions."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel


class BaseTool(ABC):
    """Abstract base class for all tools in Personal AI Core."""

    name: str
    description: str
    args_schema: Type[BaseModel]
    requires_approval: bool = False
    timeout_seconds: float = 10.0

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool action with validated parameters."""
        pass

    def to_openai_tool_schema(self) -> Dict[str, Any]:
        """Convert tool definition into the OpenAI/Groq function calling format."""
        schema = self.args_schema.model_json_schema()
        # Clean title and extra metadata
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
