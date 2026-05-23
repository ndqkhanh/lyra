"""Event system for Lyra - AG-UI compatible protocol"""

from .protocol import (
    Event,
    TurnStarted,
    ThinkingDelta,
    TextDelta,
    ToolStarted,
    ToolDelta,
    ToolFinished,
    TurnFinished,
    SubagentSpawned,
    SubagentFinished,
    StatusUpdate,
    ContextBudget,
)
from .dispatcher import EventDispatcher
from .streaming import StreamingRenderer

__all__ = [
    # Base
    "Event",
    # Turn events
    "TurnStarted",
    "ThinkingDelta",
    "TextDelta",
    "TurnFinished",
    # Tool events
    "ToolStarted",
    "ToolDelta",
    "ToolFinished",
    # Agent events
    "SubagentSpawned",
    "SubagentFinished",
    # Status events
    "StatusUpdate",
    "ContextBudget",
    # Components
    "EventDispatcher",
    "StreamingRenderer",
]
