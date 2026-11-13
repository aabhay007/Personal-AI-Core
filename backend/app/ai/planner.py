"""Autonomous Task Planner that breaks high-level goals into discrete executable steps."""
import json
import logging
from typing import List, Dict, Any, Optional
from app.ai.providers import get_llm_provider
from app.tools.registry import tool_registry

logger = logging.getLogger(__name__)

PLANNING_SYSTEM_PROMPT = """You are Personal AI Core's Autonomous Task Planner.
Your job is to decompose a user's high-level goal into a clear, minimal, sequential execution plan.

Each step in the plan must be a JSON object with:
- "step_number": integer starting at 1
- "name": short title for the step
- "description": clear explanation of what this step achieves
- "tool_name": one of the registered tool names, or null if it is a pure synthesis step
- "tool_arguments": dictionary of arguments for the tool, or empty dict
- "requires_approval": boolean. Set to TRUE if the step reads sensitive user data or executes database queries; FALSE for read-only calculations, file tree inspections, or date lookups.

Available tools:
{tool_descriptions}

Output ONLY valid JSON formatted as a list of step objects:
[
  {{
    "step_number": 1,
    "name": "...",
    "description": "...",
    "tool_name": "...",
    "tool_arguments": {{...}},
    "requires_approval": false
  }}
]
"""


class PlanGenerator:
    """Generates structured execution plans for autonomous multi-step tasks."""

    @staticmethod
    async def generate_plan(
        goal: str,
        title: Optional[str] = None,
        provider_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Decompose a high-level goal into an ordered sequence of plan steps."""
        # 1. Format available tools for prompt
        tools = tool_registry.list_tools()
        tool_desc_lines = [
            f"- {t.name}: {t.description}"
            for t in tools
        ]
        tool_descriptions = "\n".join(tool_desc_lines)

        prompt = PLANNING_SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Task Title: {title or 'Autonomous Task'}\nGoal: {goal}"}
        ]

        try:
            provider = get_llm_provider(provider_name)
            response = await provider.generate(messages=messages, temperature=0.1)
            raw_text = response.content.strip()

            # Clean JSON fences if LLM included them
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            plan = json.loads(raw_text)
            if isinstance(plan, list) and len(plan) > 0:
                return plan
        except Exception as e:
            logger.warning(f"LLM plan generation failed, falling back to deterministic plan: {e}")

        # Deterministic fallback plan if LLM is offline or returns invalid JSON
        return [
            {
                "step_number": 1,
                "name": "Inspect Environment and Context",
                "description": f"Inspect contextual workspace resources for: {goal}",
                "tool_name": "get_current_datetime",
                "tool_arguments": {},
                "requires_approval": False
            },
            {
                "step_number": 2,
                "name": "Execute Core Task Operations",
                "description": f"Perform data retrieval and analysis for: {goal}",
                "tool_name": None,
                "tool_arguments": {},
                "requires_approval": False
            },
            {
                "step_number": 3,
                "name": "Synthesize and Report Results",
                "description": "Compile execution findings and synthesize final report.",
                "tool_name": None,
                "tool_arguments": {},
                "requires_approval": False
            }
        ]
