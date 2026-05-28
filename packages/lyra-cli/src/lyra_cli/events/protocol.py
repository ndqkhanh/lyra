"""Event protocol - Pydantic models for AG-UI compatible events"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Event(BaseModel):
    """Base event class"""
    timestamp: datetime = Field(default_factory=datetime.now)


class TurnStarted(Event):
    """Turn started event"""
    type: Literal["turn.started"] = "turn.started"
    turn_id: str
    user_text: str


class ThinkingDelta(Event):
    """Thinking delta event (extended thinking)"""
    type: Literal["thinking.delta"] = "thinking.delta"
    turn_id: str
    text: str


class TextDelta(Event):
    """Text delta event (streaming response)"""
    type: Literal["text.delta"] = "text.delta"
    turn_id: str
    text: str


class ToolStarted(Event):
    """Tool started event"""
    type: Literal["tool.started"] = "tool.started"
    turn_id: str
    call_id: str
    name: str
    input: dict[str, Any]


class ToolDelta(Event):
    """Tool delta event (streaming tool output)"""
    type: Literal["tool.delta"] = "tool.delta"
    call_id: str
    chunk: str


class ToolFinished(Event):
    """Tool finished event"""
    type: Literal["tool.finished"] = "tool.finished"
    call_id: str
    status: Literal["ok", "error", "denied", "canceled"]
    output: dict[str, Any] | None = None
    duration_ms: int
    tokens_in: int = 0
    tokens_out: int = 0


class TurnFinished(Event):
    """Turn finished event"""
    type: Literal["turn.finished"] = "turn.finished"
    turn_id: str
    tokens_in: int
    tokens_out: int
    cost_usd: float = 0.0
    stop_reason: str


class SubagentSpawned(Event):
    """Subagent spawned event"""
    type: Literal["subagent.spawned"] = "subagent.spawned"
    parent_id: str | None
    agent_id: str
    goal: str


class SubagentFinished(Event):
    """Subagent finished event"""
    type: Literal["subagent.finished"] = "subagent.finished"
    agent_id: str
    status: Literal["ok", "error", "canceled"]
    tokens: int


class StatusUpdate(Event):
    """Status update event"""
    type: Literal["status.update"] = "status.update"
    segment: str
    value: str


class ContextBudget(Event):
    """Context budget event"""
    type: Literal["context.budget"] = "context.budget"
    used: int
    max: int
    system: int
    files: int
    conversation: int
    output: int
