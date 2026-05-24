"""
Frozen dataclasses for the AG-UI protocol and streaming data structures.

Defines all 16 AG-UI events across 5 categories:
  - Lifecycle: RUN_STARTED, STEP_STARTED, STEP_FINISHED, RUN_FINISHED, RUN_ERROR
  - Text: TEXT_MESSAGE_START, TEXT_MESSAGE_CONTENT, TEXT_MESSAGE_END
  - Tool: TOOL_CALL_START, TOOL_CALL_ARGS, TOOL_CALL_END, TOOL_CALL_RESULT
  - State: STATE_SNAPSHOT, STATE_DELTA (JSON Patch RFC 6902)
  - Special: INTERRUPT (HITL), CUSTOM, RAW
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any


class EventType(Enum):
    """All 16 AG-UI protocol event types across 5 categories."""

    # Lifecycle
    RUN_STARTED = auto()
    STEP_STARTED = auto()
    STEP_FINISHED = auto()
    RUN_FINISHED = auto()
    RUN_ERROR = auto()

    # Text messages
    TEXT_MESSAGE_START = auto()
    TEXT_MESSAGE_CONTENT = auto()
    TEXT_MESSAGE_END = auto()

    # Tool calls
    TOOL_CALL_START = auto()
    TOOL_CALL_ARGS = auto()
    TOOL_CALL_END = auto()
    TOOL_CALL_RESULT = auto()

    # State
    STATE_SNAPSHOT = auto()
    STATE_DELTA = auto()

    # Special
    INTERRUPT = auto()
    CUSTOM = auto()
    RAW = auto()


@dataclass(frozen=True)
class AGEvent:
    """Base event for the AG-UI protocol.

    All events carry a type discriminator, monotonic sequence number, run
    identifier, and creation timestamp so that consumers can reconstruct
    ordering and correlate events to a specific run.
    """

    type: EventType
    run_id: str
    sequence_number: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize this event to a plain dict."""
        return {
            "type": self.type.name,
            "run_id": self.run_id,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def base_from_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Extract base fields from a dict for downstream constructors."""
        return {
            "type": EventType[data["type"]],
            "run_id": data["run_id"],
            "sequence_number": data.get("sequence_number", 0),
            "timestamp": datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(timezone.utc),
        }


# ── Lifecycle events ──────────────────────────────────────────────


@dataclass(frozen=True)
class RunStartedEvent(AGEvent):
    """Emitted when a run begins."""

    input_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["input_message"] = self.input_message
        result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunStartedEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            input_message=data.get("input_message", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True)
class StepStartedEvent(AGEvent):
    """Emitted when a reasoning / tool-call step begins."""

    step_name: str = ""
    step_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["step_name"] = self.step_name
        result["step_index"] = self.step_index
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepStartedEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            step_name=data.get("step_name", ""),
            step_index=data.get("step_index", 0),
        )


@dataclass(frozen=True)
class StepFinishedEvent(AGEvent):
    """Emitted when a reasoning / tool-call step completes."""

    step_name: str = ""
    step_index: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["step_name"] = self.step_name
        result["step_index"] = self.step_index
        result["duration_ms"] = self.duration_ms
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepFinishedEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            step_name=data.get("step_name", ""),
            step_index=data.get("step_index", 0),
            duration_ms=data.get("duration_ms", 0.0),
        )


@dataclass(frozen=True)
class RunFinishedEvent(AGEvent):
    """Emitted when a run completes successfully."""

    output_message: str = ""
    total_steps: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["output_message"] = self.output_message
        result["total_steps"] = self.total_steps
        result["duration_ms"] = self.duration_ms
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunFinishedEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            output_message=data.get("output_message", ""),
            total_steps=data.get("total_steps", 0),
            duration_ms=data.get("duration_ms", 0.0),
        )


@dataclass(frozen=True)
class RunErrorEvent(AGEvent):
    """Emitted when a run terminates with an error."""

    error_code: str = ""
    error_message: str = ""
    recoverable: bool = False

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["error_code"] = self.error_code
        result["error_message"] = self.error_message
        result["recoverable"] = self.recoverable
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunErrorEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            error_code=data.get("error_code", ""),
            error_message=data.get("error_message", ""),
            recoverable=data.get("recoverable", False),
        )


# ── Text message events ───────────────────────────────────────────


@dataclass(frozen=True)
class TextMessageStartEvent(AGEvent):
    """Emitted when the agent begins producing a text message."""

    message_id: str = ""
    role: str = "assistant"

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["message_id"] = self.message_id
        result["role"] = self.role
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TextMessageStartEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            message_id=data.get("message_id", ""),
            role=data.get("role", "assistant"),
        )


@dataclass(frozen=True)
class TextMessageContentEvent(AGEvent):
    """Emitted for each token / chunk of streaming text content."""

    message_id: str = ""
    delta: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["message_id"] = self.message_id
        result["delta"] = self.delta
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TextMessageContentEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            message_id=data.get("message_id", ""),
            delta=data.get("delta", ""),
        )


@dataclass(frozen=True)
class TextMessageEndEvent(AGEvent):
    """Emitted when the agent finishes producing a text message."""

    message_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["message_id"] = self.message_id
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TextMessageEndEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            message_id=data.get("message_id", ""),
        )


# ── Tool call events ──────────────────────────────────────────────


@dataclass(frozen=True)
class ToolCallStartEvent(AGEvent):
    """Emitted when the agent initiates a tool call."""

    tool_call_id: str = ""
    tool_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["tool_call_id"] = self.tool_call_id
        result["tool_name"] = self.tool_name
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCallStartEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            tool_call_id=data.get("tool_call_id", ""),
            tool_name=data.get("tool_name", ""),
        )


@dataclass(frozen=True)
class ToolCallArgsEvent(AGEvent):
    """Emitted as tool-call arguments are streamed in."""

    tool_call_id: str = ""
    delta: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["tool_call_id"] = self.tool_call_id
        result["delta"] = self.delta
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCallArgsEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            tool_call_id=data.get("tool_call_id", ""),
            delta=data.get("delta", ""),
        )


@dataclass(frozen=True)
class ToolCallEndEvent(AGEvent):
    """Emitted when all tool-call arguments have been delivered."""

    tool_call_id: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["tool_call_id"] = self.tool_call_id
        result["tool_name"] = self.tool_name
        result["arguments"] = self.arguments
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCallEndEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            tool_call_id=data.get("tool_call_id", ""),
            tool_name=data.get("tool_name", ""),
            arguments=data.get("arguments", {}),
        )


@dataclass(frozen=True)
class ToolCallResultEvent(AGEvent):
    """Emitted after a tool has executed and produced a result."""

    tool_call_id: str = ""
    tool_name: str = ""
    result: Any = None
    is_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["tool_call_id"] = self.tool_call_id
        result["tool_name"] = self.tool_name
        result["result"] = self.result
        result["is_error"] = self.is_error
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCallResultEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            tool_call_id=data.get("tool_call_id", ""),
            tool_name=data.get("tool_name", ""),
            result=data.get("result"),
            is_error=data.get("is_error", False),
        )


# ── State events ──────────────────────────────────────────────────


@dataclass(frozen=True)
class StateSnapshotEvent(AGEvent):
    """Emitted with a full copy of the current run state.

    Clients use this to initialise or reset their local state model.
    """

    state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["state"] = self.state
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateSnapshotEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            state=data.get("state", {}),
        )


@dataclass(frozen=True)
class StateDeltaEvent(AGEvent):
    """Emitted with a JSON Patch (RFC 6902) operations list.

    Clients apply these operations to their local state model to stay
    synchronised without receiving full snapshots on every change.
    """

    operations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["operations"] = self.operations
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateDeltaEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            operations=data.get("operations", []),
        )


# ── Special events ────────────────────────────────────────────────


@dataclass(frozen=True)
class InterruptEvent(AGEvent):
    """Human-in-the-loop interrupt requesting review or approval."""

    interrupt_id: str = ""
    interrupt_type: str = ""
    message: str = ""
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["interrupt_id"] = self.interrupt_id
        result["interrupt_type"] = self.interrupt_type
        result["message"] = self.message
        result["options"] = self.options
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterruptEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            interrupt_id=data.get("interrupt_id", ""),
            interrupt_type=data.get("interrupt_type", ""),
            message=data.get("message", ""),
            options=data.get("options", []),
        )


@dataclass(frozen=True)
class CustomEvent(AGEvent):
    """Vendor- or application-specific event payload."""

    name: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["name"] = self.name
        result["payload"] = self.payload
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CustomEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            name=data.get("name", ""),
            payload=data.get("payload", {}),
        )


@dataclass(frozen=True)
class RawEvent(AGEvent):
    """Passthrough event for raw bytes / unstructured data."""

    content: str = ""
    encoding: str = "utf-8"

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["content"] = self.content
        result["encoding"] = self.encoding
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RawEvent:
        base = AGEvent.base_from_dict(data)
        return cls(
            **base,
            content=data.get("content", ""),
            encoding=data.get("encoding", "utf-8"),
        )


# ── Session & streaming data structures ───────────────────────────


@dataclass(frozen=True)
class DeviceInfo:
    """Descriptor for a connected device in a multi-device session."""

    device_id: str
    device_type: str = "unknown"
    user_agent: str = ""
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class Session:
    """A durable agent session that can survive disconnects.

    Attributes:
        session_id: Unique session identifier.
        user_id: Owning user.
        created_at: Session creation timestamp.
        last_active: Timestamp of the most recent activity.
        state: Arbitrary key-value state bag (e.g. conversation context).
        devices: Devices currently associated with the session.
        run_id: Active run identifier, if a run is in-flight.
        sequence_number: Monotonically increasing event counter for this session.
    """

    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    state: dict[str, Any] = field(default_factory=dict)
    devices: dict[str, DeviceInfo] = field(default_factory=dict)
    run_id: str | None = None
    sequence_number: int = 0


@dataclass(frozen=True)
class StreamToken:
    """A single token emitted from a streaming response.

    Attributes:
        content: The token text / content.
        position: Zero-based token index within the stream.
        timestamp: When the token was emitted.
        logprob: Optional log-probability for this token.
    """

    content: str
    position: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    logprob: float | None = None


@dataclass
class StreamState:
    """Mutable state holder for an active token stream.

    *Not* frozen because it is updated in-place during streaming.  The
    buffer is an unbounded queue of `StreamToken` objects; callers should
    apply backpressure when `buffer_size` exceeds their desired threshold.
    """

    run_id: str
    is_active: bool = True
    buffer: list[StreamToken] = field(default_factory=list)
    total_tokens: int = 0


# ── Registry for deserialization dispatch ─────────────────────────

_EVENT_CLASS_BY_TYPE: dict[EventType, type[AGEvent]] = {
    EventType.RUN_STARTED: RunStartedEvent,
    EventType.STEP_STARTED: StepStartedEvent,
    EventType.STEP_FINISHED: StepFinishedEvent,
    EventType.RUN_FINISHED: RunFinishedEvent,
    EventType.RUN_ERROR: RunErrorEvent,
    EventType.TEXT_MESSAGE_START: TextMessageStartEvent,
    EventType.TEXT_MESSAGE_CONTENT: TextMessageContentEvent,
    EventType.TEXT_MESSAGE_END: TextMessageEndEvent,
    EventType.TOOL_CALL_START: ToolCallStartEvent,
    EventType.TOOL_CALL_ARGS: ToolCallArgsEvent,
    EventType.TOOL_CALL_END: ToolCallEndEvent,
    EventType.TOOL_CALL_RESULT: ToolCallResultEvent,
    EventType.STATE_SNAPSHOT: StateSnapshotEvent,
    EventType.STATE_DELTA: StateDeltaEvent,
    EventType.INTERRUPT: InterruptEvent,
    EventType.CUSTOM: CustomEvent,
    EventType.RAW: RawEvent,
}


def get_event_class(event_type: EventType) -> type[AGEvent]:
    """Return the concrete event class for the given `EventType`."""
    return _EVENT_CLASS_BY_TYPE[event_type]
