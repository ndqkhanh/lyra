"""Tool registry with idempotency classification."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolMetadata:
    """Metadata for a registered tool."""

    name: str
    fn: Callable[..., Any]
    idempotent: bool
    description: str = ""


class ToolRegistry:
    """Registry for tools with idempotency classification."""

    def __init__(self) -> None:
        self.tools: dict[str, ToolMetadata] = {}

    def register(
        self,
        name: str,
        fn: Callable[..., Any],
        idempotent: bool = False,
        description: str = "",
    ) -> None:
        """Register a tool with idempotency flag.

        Args:
            name: Tool name
            fn: Tool function
            idempotent: Whether tool is safe for eager dispatch
            description: Tool description

        Default is idempotent=False (safe default, explicit opt-in required)
        """
        self.tools[name] = ToolMetadata(
            name=name,
            fn=fn,
            idempotent=idempotent,
            description=description,
        )

    def get(self, name: str) -> ToolMetadata | None:
        """Get tool metadata by name."""
        return self.tools.get(name)

    def is_idempotent(self, name: str) -> bool:
        """Check if tool is safe for eager dispatch."""
        tool = self.tools.get(name)
        return tool.idempotent if tool else False

    def get_function(self, name: str) -> Callable[..., Any] | None:
        """Get tool function by name."""
        tool = self.tools.get(name)
        return tool.fn if tool else None

    def list_tools(self) -> list[ToolMetadata]:
        """List all registered tools."""
        return list(self.tools.values())

    def list_idempotent(self) -> list[ToolMetadata]:
        """List all idempotent tools."""
        return [t for t in self.tools.values() if t.idempotent]


def tool(idempotent: bool = False, description: str = "") -> Callable:
    """Decorator to register a tool.

    Usage:
        @tool(idempotent=True)
        async def read_file(path: str) -> str:
            return Path(path).read_text()
    """

    def decorator(fn: Callable) -> Callable:
        fn._tool_metadata = {  # type: ignore
            "idempotent": idempotent,
            "description": description,
        }
        return fn

    return decorator
