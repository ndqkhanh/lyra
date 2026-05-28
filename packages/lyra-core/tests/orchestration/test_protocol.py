"""Tests for message protocol module."""

import json
import uuid
from datetime import datetime

import pytest
from lyra_core.orchestration.protocol import Message, MessageType


class TestMessageType:
    """Tests for MessageType enum."""

    def test_message_types(self) -> None:
        """Test all message types are defined."""
        assert MessageType.REQUEST.value == "request"
        assert MessageType.RESPONSE.value == "response"
        assert MessageType.EVENT.value == "event"
        assert MessageType.TASK.value == "task"
        assert MessageType.CONSENSUS.value == "consensus"


class TestMessage:
    """Tests for Message dataclass."""

    def test_create_message(self) -> None:
        """Test creating a message with auto-generated fields."""
        payload = {"action": "test", "data": {"key": "value"}}
        message = Message.create(
            type=MessageType.REQUEST,
            sender="agent-1",
            receiver="agent-2",
            payload=payload,
        )

        assert message.type == MessageType.REQUEST
        assert message.sender == "agent-1"
        assert message.receiver == "agent-2"
        assert message.payload == payload
        assert message.id is not None
        assert message.timestamp is not None
        assert message.trace_id is not None
        assert message.reply_to is None

    def test_create_message_with_trace_id(self) -> None:
        """Test creating a message with custom trace ID."""
        trace_id = str(uuid.uuid4())
        message = Message.create(
            type=MessageType.RESPONSE,
            sender="agent-2",
            receiver="agent-1",
            payload={},
            trace_id=trace_id,
        )

        assert message.trace_id == trace_id

    def test_create_message_with_reply_to(self) -> None:
        """Test creating a response message with reply_to."""
        reply_to = str(uuid.uuid4())
        message = Message.create(
            type=MessageType.RESPONSE,
            sender="agent-2",
            receiver="agent-1",
            payload={},
            reply_to=reply_to,
        )

        assert message.reply_to == reply_to

    def test_message_immutability(self) -> None:
        """Test that messages are immutable."""
        message = Message.create(
            type=MessageType.EVENT,
            sender="agent-1",
            receiver="broadcast",
            payload={},
        )

        with pytest.raises(AttributeError):
            message.sender = "agent-3"  # type: ignore

    def test_to_dict(self) -> None:
        """Test serializing message to dictionary."""
        payload = {"action": "test", "data": {"key": "value"}}
        message = Message.create(
            type=MessageType.REQUEST,
            sender="agent-1",
            receiver="agent-2",
            payload=payload,
        )

        data = message.to_dict()

        assert data["id"] == message.id
        assert data["type"] == "request"
        assert data["sender"] == "agent-1"
        assert data["receiver"] == "agent-2"
        assert data["payload"] == payload
        assert data["timestamp"] == message.timestamp
        assert data["trace_id"] == message.trace_id
        assert data["reply_to"] is None

    def test_to_json(self) -> None:
        """Test serializing message to JSON."""
        message = Message.create(
            type=MessageType.EVENT,
            sender="agent-1",
            receiver="broadcast",
            payload={"event": "test"},
        )

        json_str = message.to_json()
        data = json.loads(json_str)

        assert data["id"] == message.id
        assert data["type"] == "event"
        assert data["sender"] == "agent-1"

    def test_from_dict(self) -> None:
        """Test deserializing message from dictionary."""
        data = {
            "id": str(uuid.uuid4()),
            "type": "request",
            "sender": "agent-1",
            "receiver": "agent-2",
            "payload": {"action": "test"},
            "timestamp": datetime.now().isoformat(),
            "trace_id": str(uuid.uuid4()),
            "reply_to": None,
        }

        message = Message.from_dict(data)

        assert message.id == data["id"]
        assert message.type == MessageType.REQUEST
        assert message.sender == data["sender"]
        assert message.receiver == data["receiver"]
        assert message.payload == data["payload"]

    def test_from_dict_missing_fields(self) -> None:
        """Test deserializing with missing required fields."""
        data = {
            "id": str(uuid.uuid4()),
            "type": "request",
            # Missing sender, receiver, payload, timestamp
        }

        with pytest.raises(ValueError, match="Invalid message data"):
            Message.from_dict(data)

    def test_from_dict_invalid_type(self) -> None:
        """Test deserializing with invalid message type."""
        data = {
            "id": str(uuid.uuid4()),
            "type": "invalid_type",
            "sender": "agent-1",
            "receiver": "agent-2",
            "payload": {},
            "timestamp": datetime.now().isoformat(),
        }

        with pytest.raises(ValueError, match="Invalid message data"):
            Message.from_dict(data)

    def test_from_json(self) -> None:
        """Test deserializing message from JSON."""
        original = Message.create(
            type=MessageType.TASK,
            sender="orchestrator",
            receiver="agent-1",
            payload={"task": "implement_feature"},
        )

        json_str = original.to_json()
        deserialized = Message.from_json(json_str)

        assert deserialized.id == original.id
        assert deserialized.type == original.type
        assert deserialized.sender == original.sender
        assert deserialized.receiver == original.receiver
        assert deserialized.payload == original.payload

    def test_from_json_invalid(self) -> None:
        """Test deserializing from invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            Message.from_json("not valid json")

    def test_round_trip_serialization(self) -> None:
        """Test that serialization and deserialization are reversible."""
        original = Message.create(
            type=MessageType.CONSENSUS,
            sender="agent-1",
            receiver="agent-2",
            payload={"vote": "approve", "proposal_id": "123"},
            reply_to="msg-456",
        )

        # Dictionary round trip
        dict_data = original.to_dict()
        from_dict = Message.from_dict(dict_data)
        assert from_dict == original

        # JSON round trip
        json_str = original.to_json()
        from_json = Message.from_json(json_str)
        assert from_json == original
