"""Message types for Lyra CLI - inspired by Claude Code.

These message types provide a clean abstraction for agent communication,
streaming events, and session persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class SystemMessage:
    """System initialization and context compaction messages."""

    content: str
    type: Literal["system"] = "system"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "content": self.content}


@dataclass(frozen=True)
class UserMessage:
    """User prompts and tool results."""

    content: str
    type: Literal["user"] = "user"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "content": self.content}


@dataclass(frozen=True)
class AssistantMessage:
    """Agent responses with optional tool calls."""

    content: str
    tool_calls: list[dict[str, Any]] | None = None
    type: Literal["assistant"] = "assistant"

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"type": self.type, "content": self.content}
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        return data


@dataclass(frozen=True)
class ToolMessage:
    """Tool execution results."""

    content: str
    tool_call_id: str
    type: Literal["tool"] = "tool"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "content": self.content,
            "tool_call_id": self.tool_call_id,
        }


@dataclass(frozen=True)
class StreamEvent:
    """Real-time streaming events for progressive output.

    Event types:
    - text_delta: Incremental text from LLM
    - tool_call: Tool invocation started (name only)
    - tool_start: Tool execution starting (with args)
    - tool_end: Tool execution completed (with result)
    - thinking: Extended thinking output
    - status: Agent status update
    """

    event_type: Literal[
        "text_delta", "tool_call", "tool_start", "tool_end", "thinking", "status"
    ]
    data: dict[str, Any]
    agent: str | None = None  # For multi-agent attribution
    type: Literal["stream"] = "stream"

    def to_wire(self) -> str:
        """Convert to SSE wire format."""
        import json

        payload = {
            "event": self.event_type,
            "data": self.data,
        }
        if self.agent:
            payload["agent"] = self.agent
        return f"data: {json.dumps(payload)}\n\n"


@dataclass(frozen=True)
class ResultMessage:
    """Final turn summary with cost and token usage."""

    total_cost_usd: float
    tokens_in: int
    tokens_out: int
    duration_ms: int
    type: Literal["result"] = "result"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "total_cost_usd": self.total_cost_usd,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "duration_ms": self.duration_ms,
        }


# Union type for all message types
Message = (
    SystemMessage
    | UserMessage
    | AssistantMessage
    | ToolMessage
    | StreamEvent
    | ResultMessage
)
