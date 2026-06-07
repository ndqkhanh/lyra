"""
AgentsMeshBridge — Stub for external agent protocol integration.

Provides a bridge that registers external agent nodes, sends and receives
messages via a mesh protocol, and tracks node health. The full protocol
implementation (discovery, routing, security) is deferred.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MeshMessageType(Enum):
    """Types of messages in the agent mesh."""

    HEARTBEAT = "heartbeat"
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    DISCOVERY = "discovery"
    STATUS = "status"


class MeshNodeStatus(Enum):
    """Status of a mesh node."""

    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class MeshNode:
    """A node in the agent mesh.

    Attributes:
        node_id: Unique node identifier.
        name: Human-readable node name.
        status: Current node status.
        capabilities: List of capability strings.
        last_seen: Last heartbeat timestamp.
        address: Network address (host:port).
    """

    node_id: str
    name: str
    status: MeshNodeStatus = MeshNodeStatus.OFFLINE
    capabilities: list[str] = field(default_factory=list)
    last_seen: datetime | None = None
    address: str = ""


@dataclass
class MeshMessage:
    """A message exchanged across the agent mesh.

    Attributes:
        message_id: Unique message identifier.
        msg_type: Message type.
        source: Source node ID.
        target: Target node ID (or "*" for broadcast).
        payload: Message payload data.
        timestamp: When the message was created.
        reply_to: ID of message being replied to (if any).
    """

    message_id: str
    msg_type: MeshMessageType
    source: str
    target: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reply_to: str = ""


class AgentsMeshBridge:
    """Stub bridge for external agent protocol integration.

    Manages mesh nodes, sends and receives messages, and tracks
    node health. The full protocol will handle discovery, routing,
    encryption, and fault tolerance.
    """

    def __init__(self, node_id: str = "lyra-mesh-node"):
        """Initialize AgentsMeshBridge.

        Args:
            node_id: Local node identifier.
        """
        self._node_id = node_id
        self._nodes: dict[str, MeshNode] = {}
        self._messages: list[MeshMessage] = []
        self._connected: bool = False

    @property
    def node_id(self) -> str:
        """Local node identifier."""
        return self._node_id

    @property
    def connected(self) -> bool:
        """Whether the bridge is connected to the mesh."""
        return self._connected

    def connect(self) -> bool:
        """Connect to the agent mesh (stub).

        Returns:
            True if connection succeeded.
        """
        self._connected = True
        # Register self as a local node
        self.register_node(
            node_id=self._node_id,
            name="Lyra Agent",
            capabilities=["planning", "execution", "reasoning"],
        )
        return True

    def disconnect(self) -> None:
        """Disconnect from the agent mesh."""
        self._connected = False

    def register_node(
        self,
        node_id: str,
        name: str,
        capabilities: list[str] | None = None,
        address: str = "",
    ) -> bool:
        """Register a node in the mesh.

        Args:
            node_id: Unique node identifier.
            name: Human-readable name.
            capabilities: List of node capabilities.
            address: Network address.

        Returns:
            True if node was registered.
        """
        if node_id in self._nodes:
            return False

        self._nodes[node_id] = MeshNode(
            node_id=node_id,
            name=name,
            status=MeshNodeStatus.ONLINE,
            capabilities=capabilities or [],
            last_seen=datetime.now(timezone.utc),
            address=address,
        )
        return True

    def unregister_node(self, node_id: str) -> bool:
        """Remove a node from the mesh.

        Args:
            node_id: Node identifier.

        Returns:
            True if node was found and removed.
        """
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        return True

    def get_node(self, node_id: str) -> MeshNode | None:
        """Get a registered node by ID.

        Args:
            node_id: Node identifier.

        Returns:
            MeshNode or None.
        """
        return self._nodes.get(node_id)

    def list_nodes(self, status: MeshNodeStatus | None = None) -> list[MeshNode]:
        """List registered nodes, optionally filtered by status.

        Args:
            status: Filter by status.

        Returns:
            List of matching MeshNode instances.
        """
        nodes = list(self._nodes.values())
        if status is not None:
            nodes = [n for n in nodes if n.status == status]
        return nodes

    def send_message(
        self,
        target: str,
        msg_type: MeshMessageType,
        payload: dict[str, Any] | None = None,
        reply_to: str = "",
    ) -> MeshMessage:
        """Send a message to a target node.

        Args:
            target: Target node ID (or "*" for broadcast).
            msg_type: Message type.
            payload: Message payload.
            reply_to: ID of message being replied to.

        Returns:
            The sent MeshMessage.
        """
        import uuid

        message = MeshMessage(
            message_id=str(uuid.uuid4()),
            msg_type=msg_type,
            source=self._node_id,
            target=target,
            payload=payload or {},
            reply_to=reply_to,
        )
        self._messages.append(message)
        return message

    def receive_messages(
        self,
        node_id: str | None = None,
        msg_type: MeshMessageType | None = None,
    ) -> list[MeshMessage]:
        """Receive (read) messages, optionally filtered.

        Args:
            node_id: Filter by target node ID.
            msg_type: Filter by message type.

        Returns:
            List of matching messages.
        """
        results = list(self._messages)
        if node_id is not None:
            results = [m for m in results if m.target == node_id or m.target == "*"]
        if msg_type is not None:
            results = [m for m in results if m.msg_type == msg_type]
        return results

    def heartbeat(self, node_id: str) -> bool:
        """Send a heartbeat for a node.

        Args:
            node_id: Node identifier.

        Returns:
            True if node was found and updated.
        """
        node = self._nodes.get(node_id)
        if node is None:
            return False
        node.last_seen = datetime.now(timezone.utc)
        node.status = MeshNodeStatus.ONLINE
        return True

    def node_count(self, status: MeshNodeStatus | None = None) -> int:
        """Count registered nodes, optionally filtered by status.

        Args:
            status: Filter by status.

        Returns:
            Number of matching nodes.
        """
        return len(self.list_nodes(status))
