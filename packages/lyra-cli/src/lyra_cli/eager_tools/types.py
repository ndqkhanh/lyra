"""Core types for Eager Tools."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StreamChunk:
    """Streaming chunk from LLM provider."""

    tool_call_id: str | None = None
    name: str | None = None
    arguments: dict[str, Any] | None = None
    text: str | None = None


@dataclass(frozen=True)
class ToolSeal:
    """Sealed tool ready for dispatch."""

    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    sealed_at: float


@dataclass(frozen=True)
class ToolResult:
    """Tool execution result."""

    success: bool
    output: Any = None
    error: str | None = None
