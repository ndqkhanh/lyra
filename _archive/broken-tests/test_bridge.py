"""
Tests for the transport bridge module.
"""

import json
import pytest
from datetime import datetime, timezone

from lyra.transport.bridge import (
    BridgeMessage,
    BridgeMessageType,
    HeartbeatMessage,
    TransportBridge,
)


class TestBridgeMessage:
    """Tests for BridgeMessage serialization."""

    def test_to_json_creates_valid_json(self):
        """to_json should produce valid JSON with all required fields."""
        msg = BridgeMessage(
            type=BridgeMessageType.REQUEST,
            payload={"action": "run", "target": "agent"},
            id="msg-001",
        )
        raw = msg.to_json()
        parsed = json.loads(raw)
        assert parsed["type"] == "request"
        assert parsed["payload"]["action"] == "run"
        assert parsed["payload"]["target"] == "agent"
        assert parsed["id"] == "msg-001"
        assert "timestamp" in parsed

    def test_from_json_reconstructs_message(self):
        """from_json should round-trip correctly."""
        original = BridgeMessage(
            type=BridgeMessageType.RESPONSE,
            payload={"result": "ok"},
            id="msg-002",
            timestamp="2025-01-01T00:00:00+00:00",
        )
        raw = original.to_json()
        restored = BridgeMessage.from_json(raw)
        assert restored.type == BridgeMessageType.RESPONSE
        assert restored.payload == {"result": "ok"}
        assert restored.id == "msg-002"
        assert restored.timestamp == original.timestamp

    def test_default_timestamp_is_set(self):
        """A message without explicit timestamp should have one generated."""
        msg = BridgeMessage(type=BridgeMessageType.EVENT, payload={})
        assert msg.timestamp != ""
        # Should be parseable as ISO datetime
        parsed = datetime.fromisoformat(msg.timestamp)
        assert parsed.tzinfo is not None

    def test_error_message_round_trip(self):
        """Error-type messages should serialize and deserialize."""
        msg = BridgeMessage(
            type=BridgeMessageType.ERROR,
            payload={"error": "Something went wrong", "code": 500},
            id="err-001",
        )
        raw = msg.to_json()
        restored = BridgeMessage.from_json(raw)
        assert restored.type == BridgeMessageType.ERROR
        assert restored.payload["error"] == "Something went wrong"


class TestHeartbeatMessage:
    """Tests for HeartbeatMessage."""

    def test_heartbeat_message_has_correct_type(self):
        """HeartbeatMessage should always set type to HEARTBEAT."""
        hb = HeartbeatMessage(sequence=42)
        assert hb.type == BridgeMessageType.HEARTBEAT
        assert hb.payload.get("sequence") == 42

    def test_heartbeat_from_bridge(self):
        """from_bridge should preserve the original message ID."""
        original = BridgeMessage(
            type=BridgeMessageType.REQUEST,
            payload={"action": "ping"},
            id="ping-001",
        )
        hb = HeartbeatMessage.from_bridge(original, seq=7)
        assert hb.type == BridgeMessageType.HEARTBEAT
        assert hb.sequence == 7
        assert hb.id == "ping-001"

    def test_heartbeat_serialization(self):
        """Heartbeat should serialize and deserialize cleanly."""
        hb = HeartbeatMessage(sequence=99)
        raw = hb.to_json()
        restored = BridgeMessage.from_json(raw)
        assert restored.type == BridgeMessageType.HEARTBEAT
        assert restored.payload["sequence"] == 99


class TestTransportBridge:
    """Tests for TransportBridge lifecycle and handler registration."""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Bridge should start and stop cleanly."""
        bridge = TransportBridge(host="127.0.0.1", port=18765)
        assert not bridge.is_running
        await bridge.start()
        assert bridge.is_running
        await bridge.stop()
        assert not bridge.is_running

    @pytest.mark.asyncio
    async def test_no_connections_initially(self):
        """A freshly started bridge should have zero connections."""
        bridge = TransportBridge(host="127.0.0.1", port=18766)
        await bridge.start()
        assert bridge.connection_count == 0
        await bridge.stop()

    @pytest.mark.asyncio
    async def test_send_with_no_connections_does_not_raise(self):
        """Sending a message with no connections should be a no-op."""
        bridge = TransportBridge(host="127.0.0.1", port=18767)
        await bridge.start()
        msg = BridgeMessage(type=BridgeMessageType.REQUEST, payload={"test": True})
        # Should not raise
        await bridge.send(msg)
        await bridge.stop()

    @pytest.mark.asyncio
    async def test_broadcast_with_no_connections_returns_zero(self):
        """Broadcasting with no connections should return 0."""
        bridge = TransportBridge(host="127.0.0.1", port=18768)
        await bridge.start()
        msg = BridgeMessage(type=BridgeMessageType.EVENT, payload={"msg": "hello"})
        count = await bridge.broadcast(msg)
        assert count == 0
        await bridge.stop()

    @pytest.mark.asyncio
    async def test_handler_registration(self):
        """Registered handlers should be callable via dispatch."""
        bridge = TransportBridge(host="127.0.0.1", port=18769)

        received = []

        async def test_handler(msg: BridgeMessage):
            received.append(msg)
            return BridgeMessage(
                type=BridgeMessageType.RESPONSE,
                payload={"echo": msg.payload},
                id=msg.id,
            )

        bridge.on("request", test_handler)

        # Trigger dispatch directly
        request = BridgeMessage(
            type=BridgeMessageType.REQUEST,
            payload={"action": "ping"},
            id="test-001",
        )
        response = await bridge._dispatch(request)

        assert len(received) == 1
        assert received[0] is request
        assert response is not None
        assert response.payload["echo"]["action"] == "ping"

        # Remove handler and confirm no response
        bridge.off("request", test_handler)
        response2 = await bridge._dispatch(request)
        assert response2 is None

    @pytest.mark.asyncio
    async def test_handler_error_returns_error_message(self):
        """When a handler raises, an error message should be returned."""
        bridge = TransportBridge(host="127.0.0.1", port=18770)

        async def broken_handler(msg: BridgeMessage):
            raise RuntimeError("handler failure")

        bridge.on("request", broken_handler)

        request = BridgeMessage(
            type=BridgeMessageType.REQUEST,
            payload={},
            id="err-test",
        )
        response = await bridge._dispatch(request)
        assert response is not None
        assert response.type == BridgeMessageType.ERROR
        assert "handler failure" in response.payload["error"]
