"""Message schemas — the wire format between loop, LLM, and tools."""
from __future__ import annotations

import enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class StopReason(str, enum.Enum):
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    ERROR = "error"


class ToolCall(BaseModel):
    """A single tool invocation proposed by the LLM."""

    id: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """The outcome of executing a ToolCall."""

    call_id: str
    content: str
    is_error: bool = False


class Message(BaseModel):
    """A single turn in the conversation transcript.

    Roles follow the Anthropic-style convention; assistant messages may carry
    tool_calls; tool messages carry tool_results.
    """

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    stop_reason: Optional[StopReason] = None

    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)

    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role="user", content=content)

    @classmethod
    def assistant(
        cls,
        content: str = "",
        tool_calls: Optional[list[ToolCall]] = None,
        stop_reason: Optional[StopReason] = None,
    ) -> "Message":
        return cls(
            role="assistant",
            content=content,
            tool_calls=tool_calls or [],
            stop_reason=stop_reason,
        )

    @classmethod
    def tool(cls, results: list[ToolResult]) -> "Message":
        return cls(role="tool", tool_results=results)
