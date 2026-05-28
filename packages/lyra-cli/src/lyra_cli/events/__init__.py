"""Event system for Lyra - AG-UI compatible protocol"""

from .dispatcher import EventDispatcher
from .protocol import (
    ContextBudget,
    Event,
    StatusUpdate,
    SubagentFinished,
    SubagentSpawned,
    TextDelta,
    ThinkingDelta,
    ToolDelta,
    ToolFinished,
    ToolStarted,
    TurnFinished,
    TurnStarted,
)
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
