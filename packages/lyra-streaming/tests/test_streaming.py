"""
Comprehensive tests for lyra_streaming package.

Covers:
  - models: All 16 event types, enums, serialization round-trips
  - protocol: Encode, decode, validate, get_event_type
  - session: SessionManager, PresenceTracker, multi-device
  - stream: TokenStream, StreamController, backpressure
  - delta: JSON Patch (RFC 6902) diffs, apply, validation
  - websocket: Server start/stop, event echo, connection metrics
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import pytest

from lyra_streaming import (
    AGEvent,
    AGUIProtocol,
    CognitiveLatencyTier,
    ConnectionMetrics,
    CustomEvent,
    DeviceInfo,
    EventType,
    InterruptEvent,
    JSONPatch,
    Operation,
    OperationType,
    PatchError,
    PresenceTracker,
    ProtocolError,
    RawEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    Session,
    SessionError,
    SessionManager,
    StateDeltaEvent,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepStartedEvent,
    StreamController,
    StreamToken,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    TokenStream,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
    ValidationError,
    WebSocketServer,
    get_event_class,
)

# ── Models ───────────────────────────────────────────────────────────────


class TestEventType:
    """Tests for the EventType enum."""

    def test_all_16_event_types_exist(self):
        """Verify exactly 16 event types are defined."""
        members = list(EventType)
        # 5 lifecycle + 3 text + 4 tool + 2 state + 3 special = 17
        assert len(members) == 17, f"Expected 17 event types, got {len(members)}"

    def test_event_type_categories(self):
        """Verify all 5 categories are represented."""
        lifecycle = {
            EventType.RUN_STARTED,
            EventType.STEP_STARTED,
            EventType.STEP_FINISHED,
            EventType.RUN_FINISHED,
            EventType.RUN_ERROR,
        }
        text = {
            EventType.TEXT_MESSAGE_START,
            EventType.TEXT_MESSAGE_CONTENT,
            EventType.TEXT_MESSAGE_END,
        }
        tool = {
            EventType.TOOL_CALL_START,
            EventType.TOOL_CALL_ARGS,
            EventType.TOOL_CALL_END,
            EventType.TOOL_CALL_RESULT,
        }
        state = {EventType.STATE_SNAPSHOT, EventType.STATE_DELTA}
        special = {EventType.INTERRUPT, EventType.CUSTOM, EventType.RAW}

        all_members = set(EventType)
        all_expected = lifecycle | text | tool | state | special
        assert all_members == all_expected

    def test_event_type_lookup(self):
        """Verify enum lookup from string."""
        assert EventType["RUN_STARTED"] == EventType.RUN_STARTED
        assert EventType["INTERRUPT"] == EventType.INTERRUPT


class TestLifecycleEvents:
    """Tests for lifecycle event types."""

    def test_run_started_event(self):
        event = RunStartedEvent(
            type=EventType.RUN_STARTED,
            run_id="run-1",
            input_message="Hello",
            metadata={"source": "cli"},
        )
        assert event.run_id == "run-1"
        assert event.input_message == "Hello"
        assert event.metadata == {"source": "cli"}

    def test_run_started_serialization(self):
        event = RunStartedEvent(
            type=EventType.RUN_STARTED,
            run_id="run-1",
            sequence_number=1,
            input_message="Test",
        )
        d = event.to_dict()
        assert d["type"] == "RUN_STARTED"
        assert d["run_id"] == "run-1"
        assert d["input_message"] == "Test"

        restored = RunStartedEvent.from_dict(d)
        assert restored.run_id == event.run_id
        assert restored.input_message == event.input_message

    def test_step_started_event(self):
        event = StepStartedEvent(
            type=EventType.STEP_STARTED,
            run_id="run-1",
            step_name="reasoning",
            step_index=3,
        )
        assert event.step_name == "reasoning"
        assert event.step_index == 3

    def test_step_started_roundtrip(self):
        event = StepStartedEvent(
            type=EventType.STEP_STARTED,
            run_id="r",
            step_name="think",
            step_index=0,
        )
        restored = StepStartedEvent.from_dict(event.to_dict())
        assert restored.step_name == "think"

    def test_step_finished_event(self):
        event = StepFinishedEvent(
            type=EventType.STEP_FINISHED,
            run_id="run-1",
            step_name="reasoning",
            step_index=3,
            duration_ms=150.5,
        )
        d = event.to_dict()
        restored = StepFinishedEvent.from_dict(d)
        assert restored.duration_ms == 150.5

    def test_run_finished_event(self):
        event = RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            run_id="run-1",
            output_message="Done",
            total_steps=5,
            duration_ms=1200.0,
        )
        restored = RunFinishedEvent.from_dict(event.to_dict())
        assert restored.total_steps == 5

    def test_run_error_event(self):
        event = RunErrorEvent(
            type=EventType.RUN_ERROR,
            run_id="run-1",
            error_code="TIMEOUT",
            error_message="Request timed out after 30s",
            recoverable=True,
        )
        restored = RunErrorEvent.from_dict(event.to_dict())
        assert restored.error_code == "TIMEOUT"
        assert restored.recoverable is True


class TestTextMessageEvents:
    """Tests for text message event types."""

    def test_text_message_start(self):
        event = TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            run_id="run-1",
            message_id="msg-1",
            role="assistant",
        )
        d = event.to_dict()
        restored = TextMessageStartEvent.from_dict(d)
        assert restored.message_id == "msg-1"
        assert restored.role == "assistant"

    def test_text_message_content(self):
        event = TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            run_id="run-1",
            message_id="msg-1",
            delta="Hello",
        )
        restored = TextMessageContentEvent.from_dict(event.to_dict())
        assert restored.delta == "Hello"

    def test_text_message_end(self):
        event = TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            run_id="run-1",
            message_id="msg-1",
        )
        restored = TextMessageEndEvent.from_dict(event.to_dict())
        assert restored.message_id == "msg-1"


class TestToolCallEvents:
    """Tests for tool call event types."""

    def test_tool_call_start(self):
        event = ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            run_id="run-1",
            tool_call_id="tc-1",
            tool_name="search",
        )
        restored = ToolCallStartEvent.from_dict(event.to_dict())
        assert restored.tool_name == "search"

    def test_tool_call_args(self):
        event = ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS,
            run_id="run-1",
            tool_call_id="tc-1",
            delta='{"query":',
        )
        restored = ToolCallArgsEvent.from_dict(event.to_dict())
        assert restored.delta == '{"query":'

    def test_tool_call_end(self):
        event = ToolCallEndEvent(
            type=EventType.TOOL_CALL_END,
            run_id="run-1",
            tool_call_id="tc-1",
            tool_name="search",
            arguments={"query": "AI"},
        )
        restored = ToolCallEndEvent.from_dict(event.to_dict())
        assert restored.arguments == {"query": "AI"}

    def test_tool_call_result(self):
        event = ToolCallResultEvent(
            type=EventType.TOOL_CALL_RESULT,
            run_id="run-1",
            tool_call_id="tc-1",
            tool_name="search",
            result=["result1", "result2"],
            is_error=False,
        )
        restored = ToolCallResultEvent.from_dict(event.to_dict())
        assert restored.result == ["result1", "result2"]
        assert restored.is_error is False


class TestStateEvents:
    """Tests for state event types."""

    def test_state_snapshot(self):
        event = StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            run_id="run-1",
            state={"key": "value", "counter": 42},
        )
        restored = StateSnapshotEvent.from_dict(event.to_dict())
        assert restored.state == {"key": "value", "counter": 42}

    def test_state_delta(self):
        ops = [{"op": "replace", "path": "/counter", "value": 43}]
        event = StateDeltaEvent(
            type=EventType.STATE_DELTA,
            run_id="run-1",
            operations=ops,
        )
        restored = StateDeltaEvent.from_dict(event.to_dict())
        assert restored.operations == ops


class TestSpecialEvents:
    """Tests for special event types."""

    def test_interrupt_event(self):
        event = InterruptEvent(
            type=EventType.INTERRUPT,
            run_id="run-1",
            interrupt_id="h-1",
            interrupt_type="approval",
            message="Approve action?",
            options=["yes", "no"],
        )
        restored = InterruptEvent.from_dict(event.to_dict())
        assert restored.interrupt_type == "approval"
        assert restored.options == ["yes", "no"]

    def test_custom_event(self):
        event = CustomEvent(
            type=EventType.CUSTOM,
            run_id="run-1",
            name="heatmap",
            payload={"x": [1, 2, 3]},
        )
        restored = CustomEvent.from_dict(event.to_dict())
        assert restored.name == "heatmap"
        assert restored.payload == {"x": [1, 2, 3]}

    def test_raw_event(self):
        event = RawEvent(
            type=EventType.RAW,
            run_id="run-1",
            content="binary-data",
            encoding="utf-8",
        )
        restored = RawEvent.from_dict(event.to_dict())
        assert restored.content == "binary-data"


class TestAGEventBase:
    """Tests for base AGEvent."""

    def test_base_event_creation(self):
        ts = datetime.now(timezone.utc)
        event = AGEvent(
            type=EventType.RUN_STARTED,
            run_id="r1",
            sequence_number=0,
            timestamp=ts,
        )
        assert event.type == EventType.RUN_STARTED
        assert event.run_id == "r1"
        assert event.sequence_number == 0
        assert event.timestamp == ts

    def test_immutability(self):
        event = AGEvent(type=EventType.RUN_STARTED, run_id="r1")
        with pytest.raises(Exception):
            event.run_id = "r2"  # type: ignore[misc]

    def test_get_event_class(self):
        cls = get_event_class(EventType.RUN_STARTED)
        assert cls == RunStartedEvent

        cls = get_event_class(EventType.INTERRUPT)
        assert cls == InterruptEvent


class TestDeviceInfo:
    """Tests for DeviceInfo."""

    def test_device_info_create(self):
        device = DeviceInfo(device_id="dev-1", device_type="browser", user_agent="Chrome/120")
        assert device.device_id == "dev-1"
        assert device.device_type == "browser"


class TestSession:
    """Tests for Session data class."""

    def test_session_create(self):
        session = Session(session_id="s1", user_id="u1")
        assert session.session_id == "s1"
        assert session.user_id == "u1"
        assert session.state == {}
        assert session.devices == {}

    def test_session_with_state(self):
        session = Session(
            session_id="s1",
            user_id="u1",
            state={"preferences": {"theme": "dark"}},
        )
        assert session.state["preferences"]["theme"] == "dark"

    def test_session_with_devices(self):
        dev = DeviceInfo(device_id="d1")
        session = Session(session_id="s1", user_id="u1", devices={"d1": dev})
        assert session.devices["d1"].device_id == "d1"


class TestStreamToken:
    """Tests for StreamToken."""

    def test_stream_token_create(self):
        token = StreamToken(content="Hello", position=0)
        assert token.content == "Hello"
        assert token.position == 0
        assert token.logprob is None

    def test_stream_token_with_logprob(self):
        token = StreamToken(content="world", position=1, logprob=-0.5)
        assert token.logprob == -0.5


# ── Protocol ──────────────────────────────────────────────────────────────


class TestAGUIProtocol:
    """Tests for the AG-UI protocol encoder/decoder."""

    @pytest.fixture
    def protocol(self):
        return AGUIProtocol()

    def test_encode_run_started(self, protocol):
        event = RunStartedEvent(
            type=EventType.RUN_STARTED,
            run_id="run-1",
            input_message="Hi",
        )
        raw = protocol.encode(event)
        assert isinstance(raw, bytes)
        data = json.loads(raw)
        assert data["type"] == "RUN_STARTED"

    def test_decode_run_started(self, protocol):
        raw = json.dumps(
            {
                "type": "RUN_STARTED",
                "run_id": "run-1",
                "sequence_number": 0,
                "input_message": "Hi",
            }
        ).encode("utf-8")
        event = protocol.decode(raw)
        assert isinstance(event, RunStartedEvent)
        assert event.run_id == "run-1"
        assert event.input_message == "Hi"

    def test_roundtrip_all_types(self, protocol):
        """Every event type should survive encode -> decode intact."""
        events = [
            RunStartedEvent(EventType.RUN_STARTED, "r1", input_message="go"),
            StepStartedEvent(EventType.STEP_STARTED, "r1", step_name="think", step_index=0),
            StepFinishedEvent(
                EventType.STEP_FINISHED, "r1", step_name="think", step_index=0, duration_ms=100.0
            ),
            RunFinishedEvent(
                EventType.RUN_FINISHED, "r1", output_message="ok", total_steps=1, duration_ms=1000.0
            ),
            RunErrorEvent(
                EventType.RUN_ERROR, "r1", error_code="E1", error_message="oops", recoverable=False
            ),
            TextMessageStartEvent(
                EventType.TEXT_MESSAGE_START, "r1", message_id="m1", role="assistant"
            ),
            TextMessageContentEvent(
                EventType.TEXT_MESSAGE_CONTENT, "r1", message_id="m1", delta="Hi"
            ),
            TextMessageEndEvent(EventType.TEXT_MESSAGE_END, "r1", message_id="m1"),
            ToolCallStartEvent(
                EventType.TOOL_CALL_START, "r1", tool_call_id="t1", tool_name="search"
            ),
            ToolCallArgsEvent(EventType.TOOL_CALL_ARGS, "r1", tool_call_id="t1", delta='{"q":'),
            ToolCallEndEvent(
                EventType.TOOL_CALL_END,
                "r1",
                tool_call_id="t1",
                tool_name="search",
                arguments={"q": "AI"},
            ),
            ToolCallResultEvent(
                EventType.TOOL_CALL_RESULT,
                "r1",
                tool_call_id="t1",
                tool_name="search",
                result=["x"],
            ),
            StateSnapshotEvent(EventType.STATE_SNAPSHOT, "r1", state={"k": "v"}),
            StateDeltaEvent(
                EventType.STATE_DELTA, "r1", operations=[{"op": "add", "path": "/k", "value": "v"}]
            ),
            InterruptEvent(
                EventType.INTERRUPT,
                "r1",
                interrupt_id="h1",
                interrupt_type="approval",
                message="OK?",
            ),
            CustomEvent(EventType.CUSTOM, "r1", name="custom1", payload={"data": 1}),
            RawEvent(EventType.RAW, "r1", content="raw-data"),
        ]

        for original in events:
            raw = protocol.encode(original)
            restored = protocol.decode(raw)
            assert type(restored) is type(original), f"Mismatch for {original.type.name}"
            assert restored.run_id == original.run_id

    def test_decode_invalid_json(self, protocol):
        with pytest.raises(ProtocolError, match="Invalid JSON"):
            protocol.decode(b"not-json")

    def test_decode_missing_type(self, protocol):
        raw = json.dumps({"run_id": "r1"}).encode()
        with pytest.raises(ProtocolError, match="missing required 'type'"):
            protocol.decode(raw)

    def test_decode_unknown_type(self, protocol):
        raw = json.dumps({"type": "BOGUS_TYPE"}).encode()
        with pytest.raises(ProtocolError, match="Unknown event type"):
            protocol.decode(raw)

    def test_get_event_type(self, protocol):
        raw = json.dumps({"type": "RUN_ERROR", "run_id": "r1"}).encode()
        assert protocol.get_event_type(raw) == EventType.RUN_ERROR

    def test_get_event_type_invalid_json(self, protocol):
        with pytest.raises(ProtocolError):
            protocol.get_event_type(b"not json")

    def test_get_event_type_missing_type(self, protocol):
        raw = json.dumps({"run_id": "r1"}).encode()
        with pytest.raises(ProtocolError):
            protocol.get_event_type(raw)

    def test_encode_string(self, protocol):
        event = RunStartedEvent(EventType.RUN_STARTED, "r1", input_message="Hi")
        s = protocol.encode_string(event)
        assert isinstance(s, str)
        assert "RUN_STARTED" in s

    def test_validate_valid_event(self, protocol):
        event = RunStartedEvent(EventType.RUN_STARTED, "r1")
        assert protocol.validate(event) is True

    def test_validate_invalid_run_id(self, protocol):
        event = AGEvent(EventType.RUN_STARTED, "")
        with pytest.raises(ValidationError, match="non-empty string"):
            protocol.validate(event)

    def test_validate_run_error_missing_message(self, protocol):
        event = RunErrorEvent(EventType.RUN_ERROR, "r1", error_message="")
        with pytest.raises(ValidationError, match="error_message"):
            protocol.validate(event)

    def test_validate_state_delta_invalid_ops(self, protocol):
        event = StateDeltaEvent(
            EventType.STATE_DELTA, "r1", operations="not-a-list"
        )  # type: ignore[arg-type]
        with pytest.raises(ValidationError, match="must be a list"):
            protocol.validate(event)


# ── Sessions ──────────────────────────────────────────────────────────────


class TestSessionManager:
    """Tests for SessionManager and PresenceTracker."""

    @pytest.fixture
    def manager(self):
        return SessionManager()

    def test_create_session(self, manager):
        session = manager.create_session("user-1")
        assert session.session_id
        assert session.user_id == "user-1"
        assert len(manager.get_active_sessions()) == 1

    def test_create_session_with_metadata(self, manager):
        session = manager.create_session("user-1", metadata={"theme": "dark"})
        assert session.state == {"theme": "dark"}

    def test_resume_session(self, manager):
        session = manager.create_session("user-1")
        manager.create_session("user-1")  # Create another to get resume token

        # Get the resume token from internal state for testing
        token = list(manager._resume_tokens.values())[0]
        sid = session.session_id

        resumed = manager.resume_session(sid, token)
        assert resumed.session_id == sid
        assert resumed.last_active >= session.last_active

    def test_resume_invalid_token(self, manager):
        session = manager.create_session("user-1")
        with pytest.raises(SessionError, match="Invalid resume token"):
            manager.resume_session(session.session_id, "bad-token")

    def test_resume_nonexistent_session(self, manager):
        with pytest.raises(SessionError, match="not found"):
            manager.resume_session("nonexistent", "token")

    def test_close_session(self, manager):
        session = manager.create_session("user-1")
        manager.close_session(session.session_id)
        assert len(manager.get_active_sessions()) == 0

    def test_close_nonexistent_session(self, manager):
        with pytest.raises(SessionError, match="not found"):
            manager.close_session("nonexistent")

    def test_get_session(self, manager):
        session = manager.create_session("user-1")
        assert manager.get_session(session.session_id) is not None
        assert manager.get_session("nonexistent") is None

    def test_get_active_sessions(self, manager):
        assert manager.get_active_sessions() == []
        manager.create_session("u1")
        manager.create_session("u2")
        assert len(manager.get_active_sessions()) == 2

    def test_add_device(self, manager):
        session = manager.create_session("user-1")
        dev = DeviceInfo(device_id="d1", device_type="browser")
        updated = manager.add_device(session.session_id, dev)
        assert "d1" in updated.devices
        assert updated.devices["d1"].device_type == "browser"

    def test_add_device_nonexistent_session(self, manager):
        with pytest.raises(SessionError, match="not found"):
            manager.add_device("bad", DeviceInfo(device_id="d1"))

    def test_remove_device(self, manager):
        session = manager.create_session("user-1")
        manager.add_device(session.session_id, DeviceInfo(device_id="d1"))
        updated = manager.remove_device(session.session_id, "d1")
        assert "d1" not in updated.devices

    def test_broadcast(self, manager):
        session = manager.create_session("user-1")
        manager.presence.mark_connected(session.session_id, "d1")
        manager.presence.mark_connected(session.session_id, "d2")
        event = AGEvent(EventType.RUN_STARTED, "r1")
        devices = manager.broadcast(session.session_id, event)
        assert set(devices) == {"d1", "d2"}

    def test_broadcast_nonexistent_session(self, manager):
        event = AGEvent(EventType.RUN_STARTED, "r1")
        with pytest.raises(SessionError):
            manager.broadcast("bad", event)

    def test_update_state(self, manager):
        session = manager.create_session("user-1")
        updated = manager.update_state(session.session_id, {"new_key": "new_value"})
        assert updated.state == {"new_key": "new_value"}


class TestPresenceTracker:
    """Tests for PresenceTracker."""

    @pytest.fixture
    def tracker(self):
        return PresenceTracker()

    def test_mark_connected(self, tracker):
        tracker.mark_connected("s1", "d1")
        assert tracker.is_connected("s1", "d1")

    def test_mark_disconnected(self, tracker):
        tracker.mark_connected("s1", "d1")
        tracker.mark_disconnected("s1", "d1")
        assert not tracker.is_connected("s1", "d1")

    def test_get_presence(self, tracker):
        tracker.mark_connected("s1", "d1")
        tracker.mark_connected("s1", "d2")
        tracker.mark_connected("s2", "d3")
        present = tracker.get_presence("s1")
        assert present == ["d1", "d2"]
        assert tracker.get_presence("s2") == ["d3"]
        assert tracker.get_presence("s3") == []

    def test_active_sessions(self, tracker):
        tracker.mark_connected("s1", "d1")
        tracker.mark_connected("s2", "d2")
        assert set(tracker.active_sessions) == {"s1", "s2"}

    def test_disconnect_last_device(self, tracker):
        tracker.mark_connected("s1", "d1")
        tracker.mark_disconnected("s1", "d1")
        assert tracker.active_sessions == []


# ── Token Streaming ───────────────────────────────────────────────────────


class TestTokenStream:
    """Tests for TokenStream."""

    def test_create_stream(self):
        stream = TokenStream("run-1")
        assert stream.run_id == "run-1"
        assert stream.is_active
        assert stream.total_tokens == 0
        assert stream.get_buffer_size() == 0

    @pytest.mark.asyncio
    async def test_write_and_read(self):
        stream = TokenStream("run-1")
        token = StreamToken(content="Hello", position=0)

        await stream.write(token)
        assert stream.total_tokens == 1

        read_token = await stream.read()
        assert read_token is not None
        assert read_token.content == "Hello"
        assert read_token.position == 0

    @pytest.mark.asyncio
    async def test_multiple_tokens(self):
        stream = TokenStream("run-1")
        for i in range(5):
            await stream.write(StreamToken(content=f"token-{i}", position=i))

        assert stream.total_tokens == 5
        for i in range(5):
            t = await stream.read()
            assert t is not None
            assert t.content == f"token-{i}"

    @pytest.mark.asyncio
    async def test_flush(self):
        stream = TokenStream("run-1")
        await stream.write(StreamToken(content="last", position=0))
        await stream.flush()

        assert not stream.is_active
        # Sentinel None is now in the queue
        token = await stream.read()
        assert token is not None
        assert token.content == "last"

        # Second read should return None (sentinel)
        sentinel = await stream.read()
        assert sentinel is None

    @pytest.mark.asyncio
    async def test_backpressure_activates(self):
        """Backpressure activates but writes succeed when a reader drains."""
        stream = TokenStream("run-1", backpressure_threshold=3)

        # Use a reader task to drain as we write
        async def reader():
            tokens = []
            for _ in range(5):
                t = await stream.read()
                tokens.append(t)
            return tokens

        reader_task = asyncio.ensure_future(reader())

        for i in range(5):
            await stream.write(StreamToken(content=f"t-{i}", position=i))

        tokens = await reader_task
        assert len(tokens) == 5
        assert stream.total_tokens == 5

    @pytest.mark.asyncio
    async def test_apply_backpressure_runtime(self):
        stream = TokenStream("run-1", backpressure_threshold=10)
        stream.apply_backpressure(5)
        assert stream.get_buffer_size() >= 0  # Just verifying it does not crash

    def test_get_latency_tier(self):
        stream = TokenStream("run-1")
        tier = stream.get_latency_tier()
        assert isinstance(tier, CognitiveLatencyTier)
        # A fresh stream should be in PERCEPTION tier (0-400ms)
        assert tier == CognitiveLatencyTier.PERCEPTION


class TestCognitiveLatencyTier:
    """Tests for CognitiveLatencyTier classification."""

    def test_perception(self):
        assert CognitiveLatencyTier.classify(0) == CognitiveLatencyTier.PERCEPTION
        assert CognitiveLatencyTier.classify(200) == CognitiveLatencyTier.PERCEPTION
        assert CognitiveLatencyTier.classify(400) == CognitiveLatencyTier.PERCEPTION

    def test_comprehension(self):
        assert CognitiveLatencyTier.classify(401) == CognitiveLatencyTier.COMPREHENSION
        assert CognitiveLatencyTier.classify(1000) == CognitiveLatencyTier.COMPREHENSION
        assert CognitiveLatencyTier.classify(2000) == CognitiveLatencyTier.COMPREHENSION

    def test_decision(self):
        assert CognitiveLatencyTier.classify(2001) == CognitiveLatencyTier.DECISION
        assert CognitiveLatencyTier.classify(5000) == CognitiveLatencyTier.DECISION
        assert CognitiveLatencyTier.classify(10000) == CognitiveLatencyTier.DECISION

    def test_background(self):
        assert CognitiveLatencyTier.classify(10001) == CognitiveLatencyTier.BACKGROUND
        assert CognitiveLatencyTier.classify(60000) == CognitiveLatencyTier.BACKGROUND


class TestStreamController:
    """Tests for StreamController."""

    def test_create_stream(self):
        controller = StreamController()
        stream = controller.create_stream("run-1")
        assert stream.run_id == "run-1"
        assert controller.get_stream("run-1") is stream

    def test_create_duplicate_stream(self):
        controller = StreamController()
        controller.create_stream("run-1")
        with pytest.raises(ValueError, match="already exists"):
            controller.create_stream("run-1")

    def test_get_nonexistent_stream(self):
        controller = StreamController()
        assert controller.get_stream("nonexistent") is None

    @pytest.mark.asyncio
    async def test_close_stream(self):
        controller = StreamController()
        stream = controller.create_stream("run-1")
        await controller.close_stream("run-1")
        assert not stream.is_active
        assert controller.get_stream("run-1") is None

    @pytest.mark.asyncio
    async def test_close_nonexistent_stream(self):
        controller = StreamController()
        with pytest.raises(KeyError):
            await controller.close_stream("nonexistent")

    def test_get_active_streams(self):
        controller = StreamController()
        controller.create_stream("r1")
        controller.create_stream("r2")
        active = controller.get_active_streams()
        assert set(active.keys()) == {"r1", "r2"}
        assert len(active) == 2


# ── JSON Patch (RFC 6902) ─────────────────────────────────────────────────


class TestJSONPatchGenerateDiff:
    """Tests for generate_diff."""

    def test_add_key(self):
        old = {}
        new = {"name": "Alice"}
        ops = JSONPatch.generate_diff(old, new)
        assert len(ops) == 1
        assert ops[0] == {"op": "add", "path": "/name", "value": "Alice"}

    def test_remove_key(self):
        old = {"name": "Alice"}
        new = {}
        ops = JSONPatch.generate_diff(old, new)
        assert len(ops) == 1
        assert ops[0] == {"op": "remove", "path": "/name"}

    def test_replace_value(self):
        old = {"counter": 1}
        new = {"counter": 2}
        ops = JSONPatch.generate_diff(old, new)
        assert len(ops) == 1
        assert ops[0] == {"op": "replace", "path": "/counter", "value": 2}

    def test_multiple_changes(self):
        old = {"a": 1, "b": 2, "c": 3}
        new = {"a": 1, "b": 20, "d": 4}
        ops = JSONPatch.generate_diff(old, new)
        assert len(ops) == 3  # b changed, c removed, d added
        op_paths = {op["path"] for op in ops}
        assert "/b" in op_paths
        assert "/c" in op_paths
        assert "/d" in op_paths

    def test_no_changes(self):
        old = {"a": 1}
        new = {"a": 1}
        ops = JSONPatch.generate_diff(old, new)
        assert ops == []


class TestJSONPatchApplyPatch:
    """Tests for apply_patch."""

    def test_apply_add(self):
        state = {"a": 1}
        ops = [{"op": "add", "path": "/b", "value": 2}]
        result = JSONPatch.apply_patch(state, ops)
        assert result == {"a": 1, "b": 2}
        # Original must not be mutated
        assert state == {"a": 1}

    def test_apply_remove(self):
        state = {"a": 1, "b": 2}
        ops = [{"op": "remove", "path": "/b"}]
        result = JSONPatch.apply_patch(state, ops)
        assert result == {"a": 1}

    def test_apply_replace(self):
        state = {"a": 1}
        ops = [{"op": "replace", "path": "/a", "value": 99}]
        result = JSONPatch.apply_patch(state, ops)
        assert result == {"a": 99}

    def test_apply_move(self):
        state = {"a": 1, "b": 2}
        ops = [{"op": "move", "from": "/a", "path": "/c"}]
        result = JSONPatch.apply_patch(state, ops)
        assert result == {"b": 2, "c": 1}

    def test_apply_copy(self):
        state = {"a": 1, "b": 2}
        ops = [{"op": "copy", "from": "/a", "path": "/c"}]
        result = JSONPatch.apply_patch(state, ops)
        assert result == {"a": 1, "b": 2, "c": 1}

    def test_apply_test_passes(self):
        state = {"a": 1}
        ops = [{"op": "test", "path": "/a", "value": 1}]
        result = JSONPatch.apply_patch(state, ops)
        assert result == {"a": 1}

    def test_apply_test_fails(self):
        state = {"a": 1}
        ops = [{"op": "test", "path": "/a", "value": 2}]
        with pytest.raises(PatchError, match="TEST failed"):
            JSONPatch.apply_patch(state, ops)

    def test_apply_unknown_op(self):
        state = {"a": 1}
        ops = [{"op": "invalid_op", "path": "/a"}]
        with pytest.raises(PatchError, match="Unknown operation"):
            JSONPatch.apply_patch(state, ops)

    def test_apply_nested_path(self):
        state = {"user": {"name": "Alice", "age": 30}}
        ops = [{"op": "replace", "path": "/user/age", "value": 31}]
        result = JSONPatch.apply_patch(state, ops)
        assert result["user"]["age"] == 31

    def test_apply_with_list(self):
        state = {"items": ["a", "b", "c"]}
        ops = [{"op": "add", "path": "/items/1", "value": "x"}]
        result = JSONPatch.apply_patch(state, ops)
        assert result["items"] == ["a", "x", "b", "c"]

    def test_apply_list_append(self):
        state = {"items": ["a"]}
        ops = [{"op": "add", "path": "/items/-", "value": "b"}]
        result = JSONPatch.apply_patch(state, ops)
        assert result["items"] == ["a", "b"]


class TestJSONPatchValidate:
    """Tests for validate_patch."""

    def test_valid_operations(self):
        ops = [{"op": "add", "path": "/x", "value": 1}]
        assert JSONPatch.validate_patch(ops) is True

    def test_invalid_op_type(self):
        ops = [{"op": "invalid", "path": "/x"}]
        with pytest.raises(PatchError, match="Invalid op"):
            JSONPatch.validate_patch(ops)

    def test_missing_path(self):
        ops = [{"op": "add"}]
        with pytest.raises(PatchError, match="Missing 'path'"):
            JSONPatch.validate_patch(ops)

    def test_not_a_dict(self):
        ops = ["not-a-dict"]  # type: ignore[list-item]
        with pytest.raises(PatchError, match="not a dict"):
            JSONPatch.validate_patch(ops)


class TestOperationDataclass:
    """Tests for Operation dataclass."""

    def test_operation_to_dict(self):
        op = Operation(op=OperationType.ADD, path="/name", value="Alice")
        d = op.to_dict()
        assert d == {"op": "add", "path": "/name", "value": "Alice"}

    def test_operation_with_from(self):
        op = Operation(op=OperationType.COPY, path="/b", value=None, from_="/a")
        d = op.to_dict()
        assert d["from"] == "/a"


# ── WebSocket Server ──────────────────────────────────────────────────────


class TestWebSocketServer:
    """Tests for the async WebSocket server."""

    @pytest.fixture
    def server(self):
        return WebSocketServer()

    @pytest.mark.asyncio
    async def test_start_stop(self, server):
        """Test that the server can start and stop cleanly."""
        await server.start("127.0.0.1", 18765)
        assert server._server is not None
        await server.stop()
        assert server._server is None

    @pytest.mark.asyncio
    async def test_send_receive_event(self, server):
        """Test sending and receiving events over a raw TCP connection."""
        await server.start("127.0.0.1", 18766)

        # Connect a client
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", 18766), timeout=5.0
        )

        try:
            # Send an event
            event = RunStartedEvent(
                type=EventType.RUN_STARTED,
                run_id="test-run",
                input_message="Hello, server",
            )
            raw = json.dumps(event.to_dict()).encode("utf-8") + b"\n"
            writer.write(raw)
            await writer.drain()

            # Read the echoed ack
            response = await asyncio.wait_for(reader.readline(), timeout=5.0)
            decoded = json.loads(response.strip())
            assert decoded["type"] == "RAW"
            assert decoded["run_id"] == "test-run"
        finally:
            writer.close()
            await writer.wait_closed()
            await server.stop()

    @pytest.mark.asyncio
    async def test_connection_stats(self, server):
        """Test that connection metrics are tracked."""
        await server.start("127.0.0.1", 18767)

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", 18767), timeout=5.0
        )

        try:
            event = RunStartedEvent(
                type=EventType.RUN_STARTED,
                run_id="stats-test",
                input_message="ping",
            )
            raw = json.dumps(event.to_dict()).encode("utf-8") + b"\n"
            writer.write(raw)
            await writer.drain()

            await asyncio.wait_for(reader.readline(), timeout=5.0)

            stats = server.get_connection_stats()
            assert stats["total_connections"] >= 1
            assert stats["total_events_sent"] >= 1
            assert stats["total_events_received"] >= 1
            assert stats["uptime_seconds"] >= 0
        finally:
            writer.close()
            await writer.wait_closed()
            await server.stop()

    @pytest.mark.asyncio
    async def test_session_manager_integration(self):
        """Test that the server integrates with SessionManager."""
        sm = SessionManager()
        svr = WebSocketServer(session_manager=sm)
        assert svr.session_manager is sm

    @pytest.mark.asyncio
    async def test_broadcast_event(self, server):
        sm = server.session_manager
        session = sm.create_session("user-1")
        sm.presence.mark_connected(session.session_id, "d1")
        sm.presence.mark_connected(session.session_id, "d2")

        event = AGEvent(EventType.RUN_STARTED, "r1")
        devices = await server.broadcast_event(event, session.session_id)
        assert set(devices) == {"d1", "d2"}


class TestConnectionMetrics:
    """Tests for ConnectionMetrics."""

    def test_defaults(self):
        m = ConnectionMetrics()
        assert m.total_connections == 0
        assert m.active_connections == 0

    def test_to_dict(self):
        m = ConnectionMetrics()
        d = m.to_dict()
        assert "total_connections" in d
        assert "uptime_seconds" in d
        assert d["uptime_seconds"] >= 0


# ── Integration scenarios ─────────────────────────────────────────────────


class TestIntegrationScenarios:
    """End-to-end integration scenarios."""

    @pytest.mark.asyncio
    async def test_streaming_to_protocol_pipeline(self):
        """Tokens flow through streaming -> protocol -> transport."""
        stream = TokenStream("run-1")
        protocol = AGUIProtocol()

        # Produce tokens
        await stream.write(StreamToken(content="Hello", position=0))
        await stream.write(StreamToken(content=" world", position=1))
        await stream.flush()

        # Consume and wrap in events
        events: list[AGEvent] = []
        while True:
            token = await stream.read()
            if token is None:
                break
            event = TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                run_id="run-1",
                message_id="msg-1",
                delta=token.content,
            )
            events.append(event)

        # Encode/decode round-trip
        for original in events:
            raw = protocol.encode(original)
            restored = protocol.decode(raw)
            assert isinstance(restored, TextMessageContentEvent)
            assert restored.delta == original.delta

    @pytest.mark.asyncio
    async def test_session_with_presence_and_broadcast(self):
        """Full lifecycle: session + devices + presence + broadcast."""
        sm = SessionManager()

        # Create session
        session = sm.create_session("user-1")

        # Add devices
        sm.add_device(session.session_id, DeviceInfo(device_id="d1", device_type="browser"))
        sm.add_device(session.session_id, DeviceInfo(device_id="d2", device_type="mobile"))

        # Mark some online
        sm.presence.mark_connected(session.session_id, "d1")

        # Broadcast should only include online devices
        event = AGEvent(EventType.RUN_STARTED, "r1")
        devices = sm.broadcast(session.session_id, event)
        assert devices == ["d1"]

    @pytest.mark.asyncio
    async def test_state_delta_workflow(self):
        """Snapshot -> delta -> apply workflow."""
        state = {"counter": 0, "status": "idle"}

        # Emit snapshot
        snap = StateSnapshotEvent(EventType.STATE_SNAPSHOT, "r1", state=state)
        assert snap.state == state

        # Mutate
        new_state = {**state, "counter": 1, "status": "running"}
        ops = JSONPatch.generate_diff(state, new_state)

        # Emit delta
        delta = StateDeltaEvent(EventType.STATE_DELTA, "r1", operations=ops)
        assert len(delta.operations) > 0

        # Apply delta to verify
        applied = JSONPatch.apply_patch(state, ops)
        assert applied["counter"] == 1
        assert applied["status"] == "running"
