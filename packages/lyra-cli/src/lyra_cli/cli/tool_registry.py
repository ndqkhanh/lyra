"""Tool registry for LLM tool calling."""
from typing import Callable, Any
import json


class ToolRegistry:
    """Registry of tools available to the LLM."""

    def __init__(self):
        self._tools: dict[str, dict] = {}
        self._executors: dict[str, Callable] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        executor: Callable,
        idempotent: bool = False,
    ) -> None:
        """Register a tool."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "input_schema": parameters,
        }
        self._executors[name] = executor
        # Store idempotency flag for eager dispatch
        self._tools[name]["_idempotent"] = idempotent

    def get_tool_definitions(self) -> list[dict]:
        """Get tool definitions for LLM (Anthropic format)."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["input_schema"],
            }
            for t in self._tools.values()
        ]

    def is_idempotent(self, tool_name: str) -> bool:
        """Check if tool is safe for eager dispatch."""
        return self._tools.get(tool_name, {}).get("_idempotent", False)

    async def execute(self, tool_name: str, arguments: str) -> Any:
        """Execute a tool with JSON arguments."""
        executor = self._executors.get(tool_name)
        if not executor:
            raise ValueError(f"Tool {tool_name} not found")

        args = json.loads(arguments) if arguments else {}
        return await executor(**args)
