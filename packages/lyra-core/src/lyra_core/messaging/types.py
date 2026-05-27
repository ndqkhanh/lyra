"""Message types for cross-component communication."""
from enum import Enum


class MessageType(str, Enum):
    """Message type enumeration.

    Defines all message types that can be published through the event bus.
    """

    # Agent lifecycle
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"

    # Tool execution
    TOOL_EXECUTED = "tool.executed"
    TOOL_FAILED = "tool.failed"

    # Memory operations
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"

    # Errors
    ERROR_OCCURRED = "error.occurred"

    # System events
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"
