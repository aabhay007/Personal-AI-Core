"""Base Agent class defining autonomous behavior and tool permissions."""
from abc import ABC
from typing import List, Optional


class BaseAgent(ABC):
    """Abstract base class for specialized AI agents."""
    name: str
    description: str
    system_prompt: str
    allowed_tools: Optional[List[str]] = None

    def get_system_prompt(self) -> str:
        return self.system_prompt
