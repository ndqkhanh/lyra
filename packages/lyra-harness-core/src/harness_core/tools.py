"""Tool abstraction: base class, registry, typed-arg validation, schema export."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from .messages import ToolCall, ToolResult


class ToolError(Exception):
    """Raised by tools to signal a structured, model-visible failure."""


class Tool(ABC):
    """Base class for a tool the agent may invoke.

    Subclasses override ``name``, ``description``, ``ArgsModel`` (pydantic), and
    ``run(args) -> str | dict``. The registry validates args before dispatch.
    """

    name: str = ""
    description: str = ""
    risk: str = "low"  # low | medium | high | destructive
    writes: bool = False  # true if the tool mutates external state

    class ArgsModel(BaseModel):  # override in subclasses
        pass

    @abstractmethod
    def run(self, args: Any) -> str:
        """Execute the tool and return stringified output."""
        raise NotImplementedError

    def to_schema(self) -> dict[str, Any]:
        """Emit an Anthropic-compatible tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.ArgsModel.model_json_schema(),
        }


class ToolRegistry:
    """Holds registered tools; dispatches ToolCall → ToolResult with validation."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError(f"Tool {type(tool).__name__} has empty .name")
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} already registered")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def schemas(self, allowed: Optional[set[str]] = None) -> list[dict[str, Any]]:
        """Emit schemas for all tools (or a subset by name)."""
        return [
            t.to_schema()
            for n, t in self._tools.items()
            if allowed is None or n in allowed
        ]

    def execute(self, call: ToolCall) -> ToolResult:
        """Validate args and dispatch to the tool; wrap errors into ToolResult."""
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(
                call_id=call.id,
                content=f"Unknown tool: {call.name!r}",
                is_error=True,
            )
        try:
            args = tool.ArgsModel(**call.args)
        except ValidationError as e:
            return ToolResult(
                call_id=call.id,
                content=f"argument validation failed: {e.errors()}",
                is_error=True,
            )
        try:
            output = tool.run(args)
        except ToolError as e:
            return ToolResult(call_id=call.id, content=str(e), is_error=True)
        except Exception as e:  # noqa: BLE001 - intentional broad catch at tool boundary
            return ToolResult(
                call_id=call.id,
                content=f"unhandled tool error: {type(e).__name__}: {e}",
                is_error=True,
            )
        if not isinstance(output, str):
            output = str(output)
        return ToolResult(call_id=call.id, content=output, is_error=False)
