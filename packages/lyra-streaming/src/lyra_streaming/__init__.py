"""
Lyra Streaming - Real-time interaction for Lyra AGI.

Implements:
  - AG-UI Protocol (16 event types across 5 categories)
  - Durable Sessions with multi-device fan-out and presence
  - Token-level streaming with backpressure
  - JSON Patch (RFC 6902) state deltas
  - Async WebSocket server
"""

from lyra_streaming.delta import JSONPatch, Operation, OperationType, PatchError
from lyra_streaming.models import (
    AGEvent,
    CustomEvent,
    DeviceInfo,
    EventType,
    InterruptEvent,
    RawEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    Session,
    StateDeltaEvent,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepStartedEvent,
    StreamState,
    StreamToken,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
    get_event_class,
)
from lyra_streaming.protocol import AGUIProtocol, ProtocolError, ValidationError
from lyra_streaming.session import PresenceTracker, SessionError, SessionManager
from lyra_streaming.stream import CognitiveLatencyTier, StreamController, TokenStream
from lyra_streaming.websocket import ConnectionMetrics, WebSocketServer

__version__ = "0.1.0"

__all__ = [
    # Protocol
    "AGUIProtocol",
    "ProtocolError",
    "ValidationError",
    # Events
    "AGEvent",
    "EventType",
    "RunStartedEvent",
    "StepStartedEvent",
    "StepFinishedEvent",
    "RunFinishedEvent",
    "RunErrorEvent",
    "TextMessageStartEvent",
    "TextMessageContentEvent",
    "TextMessageEndEvent",
    "ToolCallStartEvent",
    "ToolCallArgsEvent",
    "ToolCallEndEvent",
    "ToolCallResultEvent",
    "StateSnapshotEvent",
    "StateDeltaEvent",
    "InterruptEvent",
    "CustomEvent",
    "RawEvent",
    "get_event_class",
    # Sessions
    "Session",
    "DeviceInfo",
    "SessionManager",
    "PresenceTracker",
    "SessionError",
    # Streaming
    "StreamToken",
    "StreamState",
    "TokenStream",
    "StreamController",
    "CognitiveLatencyTier",
    # State deltas
    "JSONPatch",
    "Operation",
    "OperationType",
    "PatchError",
    # WebSocket
    "WebSocketServer",
    "ConnectionMetrics",
]
