"""Tests for src/agents_mesh/bridge.py."""
from __future__ import annotations

import pytest

from src.agents_mesh.bridge import (
    AgentsMeshBridge,
    MeshMessage,
    MeshMessageType,
    MeshNode,
    MeshNodeStatus,
)


class TestMeshNode:
    """Tests for MeshNode."""

    def test_default_status_offline(self):
        """Default MeshNode status is OFFLINE."""
        node = MeshNode(node_id="n1", name="Test")
        assert node.status == MeshNodeStatus.OFFLINE

    def test_custom_status(self):
        """Custom status is preserved."""
        node = MeshNode(node_id="n1", name="Test", status=MeshNodeStatus.BUSY)
        assert node.status == MeshNodeStatus.BUSY


class TestMeshMessage:
    """Tests for MeshMessage."""

    def test_default_payload_empty(self):
        """Default payload is an empty dict."""
        msg = MeshMessage(
            message_id="m1",
            msg_type=MeshMessageType.HEARTBEAT,
            source="src",
            target="tgt",
        )
        assert msg.payload == {}


class TestAgentsMeshBridge:
    """Tests for AgentsMeshBridge."""

    def test_initial_state(self):
        """Bridge starts disconnected with zero nodes."""
        bridge = AgentsMeshBridge(node_id="test-node")
        assert bridge.connected is False
        assert bridge.node_count() == 0

    def test_connect(self):
        """Connecting registers the local node."""
        bridge = AgentsMeshBridge(node_id="test-node")
        assert bridge.connect() is True
        assert bridge.connected is True
        assert bridge.node_count() >= 1

    def test_register_node(self):
        """Registering a node adds it to the mesh."""
        bridge = AgentsMeshBridge()
        bridge.connect()
        result = bridge.register_node("worker-1", "Worker One", capabilities=["execution"])
        assert result is True
        assert bridge.node_count() == 2  # local + worker
        node = bridge.get_node("worker-1")
        assert node is not None
        assert node.capabilities == ["execution"]

    def test_register_duplicate_returns_false(self):
        """Registering the same node ID twice returns False."""
        bridge = AgentsMeshBridge()
        bridge.connect()
        bridge.register_node("dup", "First")
        assert bridge.register_node("dup", "Second") is False

    def test_unregister_node(self):
        """Unregistering a node removes it."""
        bridge = AgentsMeshBridge()
        bridge.connect()
        bridge.register_node("gone", "Gone")
        assert bridge.unregister_node("gone") is True
        assert bridge.get_node("gone") is None

    def test_send_message(self):
        """send_message creates and stores a message."""
        bridge = AgentsMeshBridge()
        bridge.connect()
        msg = bridge.send_message(
            "worker-1",
            MeshMessageType.TASK,
            payload={"action": "compute"},
        )
        assert msg.source == bridge.node_id
        assert msg.target == "worker-1"
        assert msg.msg_type == MeshMessageType.TASK
        assert len(bridge.receive_messages()) == 1

    def test_heartbeat_updates_status(self):
        """Heartbeat sets node status to ONLINE and updates last_seen."""
        bridge = AgentsMeshBridge()
        bridge.connect()
        bridge.register_node("hb-node", "HB")
        assert bridge.heartbeat("hb-node") is True
        node = bridge.get_node("hb-node")
        assert node is not None
        assert node.status == MeshNodeStatus.ONLINE
        assert node.last_seen is not None

    def test_list_nodes_filtered(self):
        """list_nodes can filter by status."""
        bridge = AgentsMeshBridge()
        bridge.connect()
        bridge.register_node("online-1", "Online1")
        bridge.register_node("online-2", "Online2")
        # Both are ONLINE after connect+register
        online = bridge.list_nodes(status=MeshNodeStatus.ONLINE)
        assert len(online) >= 2
        offline = bridge.list_nodes(status=MeshNodeStatus.OFFLINE)
        assert len(offline) == 0
