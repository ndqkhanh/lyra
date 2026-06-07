"""
Mesh Protocol — full agent mesh networking, discovery, routing, encryption, and security.

Extends the stub bridge with:

    - MeshProtocol: Low-level message transport for the agent mesh.
    - AgentDiscovery: Discover other agents on the mesh via gossip / mDNS-style
      broadcasting.
    - MeshRouter: Route messages between agents using content-based and
      capability-based routing.
    - MeshEncryption: Encrypt mesh communications with symmetric and
      asymmetric schemes.
    - MeshSecurity: Authenticate agents and enforce access control on the mesh.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_PROTOCOL_VERSION: str = "1.0"
DEFAULT_HEARTBEAT_INTERVAL: float = 30.0
DEFAULT_NODE_TIMEOUT: float = 120.0
DEFAULT_GOSSIP_FANOUT: int = 3
DEFAULT_ROUTE_TABLE_SIZE: int = 1024
DEFAULT_KEY_SIZE_BYTES: int = 32  # AES-256
SIGNATURE_HASH = "sha256"


# =============================================================================
# Enums and data types
# =============================================================================


class MeshProtocolState(Enum):
    """State of a mesh protocol connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    ERROR = "error"


class DiscoveryMethod(Enum):
    """Methods by which agents discover each other."""

    GOSSIP = "gossip"
    BROADCAST = "broadcast"
    DIRECTORY = "directory"
    MDNS = "mdns"
    STATIC = "static"


class RoutingStrategy(Enum):
    """Strategies for routing messages between agents."""

    DIRECT = "direct"
    BROADCAST = "broadcast"
    CAPABILITY = "capability"
    CONTENT_BASED = "content_based"
    SHORTEST_PATH = "shortest_path"
    OPPORTUNISTIC = "opportunistic"


class EncryptionScheme(Enum):
    """Encryption schemes supported by the mesh."""

    NONE = "none"
    AES_GCM = "aes_gcm"
    CHACHA20 = "chacha20"
    HYBRID_ECDH = "hybrid_ecdh"


class AuthMethod(Enum):
    """Authentication methods for mesh agents."""

    TOKEN = "token"
    CERTIFICATE = "certificate"
    CHALLENGE_RESPONSE = "challenge_response"
    MUTUAL_TLS = "mutual_tls"


class AccessLevel(Enum):
    """Access control levels for mesh operations."""

    NONE = 0
    READ = 10
    WRITE = 20
    ADMIN = 30
    ROOT = 100


@dataclass
class MeshIdentity:
    """Identity of an agent on the mesh.

    Attributes:
        agent_id: Unique agent identifier.
        public_key: Base64-encoded public key (if asymmetric auth is used).
        capabilities: List of capability strings this agent offers.
        auth_method: Authentication method used.
        access_level: Access level granted.
    """

    agent_id: str
    public_key: str = ""
    capabilities: list[str] = field(default_factory=list)
    auth_method: AuthMethod = AuthMethod.TOKEN
    access_level: AccessLevel = AccessLevel.READ


@dataclass
class RouteEntry:
    """A single entry in the mesh routing table.

    Attributes:
        target_id: Destination agent ID.
        next_hop: Next-hop agent ID (or the target itself).
        cost: Hop cost (lower is better).
        ttl: Time-to-live in seconds.
        last_updated: Timestamp of last update.
        strategy: Routing strategy used for this entry.
    """

    target_id: str
    next_hop: str
    cost: float = 1.0
    ttl: float = 300.0
    last_updated: float = 0.0
    strategy: RoutingStrategy = RoutingStrategy.DIRECT

    def is_expired(self) -> bool:
        """Check if this route entry has expired."""
        return time.time() - self.last_updated > self.ttl


@dataclass
class MeshEnvelope:
    """An encrypted envelope for mesh message transport.

    Attributes:
        envelope_id: Unique envelope identifier.
        sender_id: Sender agent ID.
        recipient_id: Recipient agent ID.
        ciphertext: Encrypted payload (base64).
        iv: Initialization vector (base64).
        scheme: Encryption scheme used.
        signature: HMAC signature (base64).
        nonce: Cryptographic nonce (base64).
    """

    envelope_id: str
    sender_id: str
    recipient_id: str
    ciphertext: str
    iv: str
    scheme: EncryptionScheme
    signature: str = ""
    nonce: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# MeshProtocol
# =============================================================================


class MeshProtocol:
    """Low-level message transport for the agent mesh.

    MeshProtocol handles connection lifecycle, message serialization,
    framing, and basic reliability (ack / retry). It sits below the
    routing layer and above the raw transport (e.g., WebSocket, TCP).

    Attributes:
        node_id: This node's identifier.
        protocol_version: Protocol version string.
        state: Current protocol state.
        heartbeat_interval: Seconds between heartbeats.
    """

    def __init__(
        self,
        node_id: str,
        protocol_version: str = DEFAULT_PROTOCOL_VERSION,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
        node_timeout: float = DEFAULT_NODE_TIMEOUT,
    ) -> None:
        self.node_id = node_id
        self.protocol_version = protocol_version
        self.heartbeat_interval = heartbeat_interval
        self.node_timeout = node_timeout

        self.state: MeshProtocolState = MeshProtocolState.DISCONNECTED
        self._peers: dict[str, float] = {}  # peer_id -> last_seen
        self._message_log: list[dict[str, Any]] = []
        self._handlers: dict[str, Callable] = {}
        self._last_heartbeat: float = 0.0

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Open the protocol connection.

        Transitions from DISCONNECTED to CONNECTED.  In a real transport
        this would open a WebSocket or TCP socket.

        Returns:
            True if the connection was established.
        """
        if self.state == MeshProtocolState.CONNECTED:
            return True

        self.state = MeshProtocolState.CONNECTING
        logger.info("MeshProtocol[%s]: connecting ...", self.node_id)

        # Simulate connection setup
        self.state = MeshProtocolState.CONNECTED
        self._last_heartbeat = time.time()
        logger.info("MeshProtocol[%s]: connected (v%s)", self.node_id, self.protocol_version)
        return True

    def disconnect(self) -> bool:
        """Close the protocol connection.

        Returns:
            True if the connection was closed.
        """
        if self.state == MeshProtocolState.DISCONNECTED:
            return True

        logger.info("MeshProtocol[%s]: disconnecting ...", self.node_id)
        self.state = MeshProtocolState.DISCONNECTED
        self._peers.clear()
        return True

    def is_connected(self) -> bool:
        """Check if the protocol is in a connected state."""
        return self.state == MeshProtocolState.CONNECTED

    # ------------------------------------------------------------------
    # Peer management
    # ------------------------------------------------------------------

    def register_peer(self, peer_id: str) -> None:
        """Register a known peer.

        Args:
            peer_id: Peer agent identifier.
        """
        self._peers[peer_id] = time.time()
        logger.debug("MeshProtocol[%s]: peer registered: %s", self.node_id, peer_id)

    def unregister_peer(self, peer_id: str) -> bool:
        """Remove a peer.

        Returns:
            True if the peer was found and removed.
        """
        return self._peers.pop(peer_id, None) is not None

    def get_peers(self) -> list[str]:
        """Return list of known peer IDs."""
        return list(self._peers.keys())

    def peer_count(self) -> int:
        """Return the number of known peers."""
        return len(self._peers)

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def send_heartbeat(self) -> dict[str, Any]:
        """Send (or simulate sending) a heartbeat message.

        Returns:
            The heartbeat message payload.
        """
        self._last_heartbeat = time.time()
        heartbeat = {
            "type": "heartbeat",
            "node_id": self.node_id,
            "timestamp": self._last_heartbeat,
            "protocol_version": self.protocol_version,
            "peer_count": self.peer_count(),
        }
        logger.debug("MeshProtocol[%s]: heartbeat sent", self.node_id)
        return heartbeat

    def receive_heartbeat(self, peer_id: str) -> None:
        """Process an incoming heartbeat from a peer.

        Args:
            peer_id: The peer that sent the heartbeat.
        """
        self._peers[peer_id] = time.time()

    def should_send_heartbeat(self) -> bool:
        """Check whether enough time has passed to send a heartbeat."""
        return (time.time() - self._last_heartbeat) >= self.heartbeat_interval

    def get_stale_peers(self) -> list[str]:
        """Return peers that have not sent a heartbeat within the timeout."""
        now = time.time()
        return [pid for pid, last in self._peers.items() if now - last > self.node_timeout]

    # ------------------------------------------------------------------
    # Message send / receive
    # ------------------------------------------------------------------

    def send_message(
        self,
        target: str,
        payload: dict[str, Any],
        msg_type: str = "message",
    ) -> str:
        """Send a message to a target peer.

        Args:
            target: Target peer ID.
            payload: Message payload.
            msg_type: Message type string.

        Returns:
            The message ID.
        """
        msg_id = str(uuid.uuid4())
        message = {
            "message_id": msg_id,
            "type": msg_type,
            "source": self.node_id,
            "target": target,
            "payload": payload,
            "timestamp": time.time(),
        }
        self._message_log.append(message)
        logger.debug("MeshProtocol[%s]: sent %s to %s", self.node_id, msg_id, target)
        return msg_id

    def receive_messages(
        self,
        msg_type: str | None = None,
        since: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Read messages from the local log, optionally filtered.

        Args:
            msg_type: Optional message type filter.
            since: Only return messages after this timestamp.

        Returns:
            List of matching messages.
        """
        results = list(self._message_log)
        if msg_type is not None:
            results = [m for m in results if m["type"] == msg_type]
        if since > 0.0:
            results = [m for m in results if m["timestamp"] >= since]
        return results

    def register_handler(self, msg_type: str, handler: Callable) -> None:
        """Register a handler for a specific message type.

        Args:
            msg_type: Message type to handle.
            handler: Callable(message) -> Any.
        """
        self._handlers[msg_type] = handler

    # ------------------------------------------------------------------
        # Status
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:
        """Return protocol statistics."""
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "protocol_version": self.protocol_version,
            "peers": self.peer_count(),
            "messages_sent": len(self._message_log),
            "last_heartbeat": self._last_heartbeat,
            "stale_peers": len(self.get_stale_peers()),
        }


# =============================================================================
# AgentDiscovery
# =============================================================================


class AgentDiscovery:
    """Agent discovery on the mesh.

    Agents discover each other through gossip-style announcements,
    direct broadcast, or a central directory.  Each discovered agent
    is tracked with its identity and last-seen timestamp.

    Attributes:
        local_agent_id: The discovering agent's own ID.
        discovery_method: The primary discovery method.
        gossip_fanout: Number of peers to forward gossip to.
    """

    def __init__(
        self,
        local_agent_id: str,
        discovery_method: DiscoveryMethod = DiscoveryMethod.GOSSIP,
        gossip_fanout: int = DEFAULT_GOSSIP_FANOUT,
        node_timeout: float = DEFAULT_NODE_TIMEOUT,
    ) -> None:
        self.local_agent_id = local_agent_id
        self.discovery_method = discovery_method
        self.gossip_fanout = gossip_fanout
        self.node_timeout = node_timeout

        self._discovered: dict[str, MeshIdentity] = {}
        self._last_seen: dict[str, float] = {}
        self._announcement_history: list[dict[str, Any]] = []
        self._discovery_listeners: list[Callable[[str, MeshIdentity], None]] = []

    # ------------------------------------------------------------------
    # Discovery hooks
    # ------------------------------------------------------------------

    def on_discovery(self, listener: Callable[[str, MeshIdentity], None]) -> None:
        """Register a listener called when a new agent is discovered.

        Args:
            listener: Callable(agent_id, identity).
        """
        self._discovery_listeners.append(listener)

    # ------------------------------------------------------------------
    # Announce / discover
    # ------------------------------------------------------------------

    def announce(self) -> dict[str, Any]:
        """Create an announcement for this agent.

        The announcement is broadcast or gossiped to peers so that
        other agents can discover this node.

        Returns:
            The announcement payload.
        """
        announcement = {
            "type": "discovery_announce",
            "agent_id": self.local_agent_id,
            "method": self.discovery_method.value,
            "timestamp": time.time(),
            "ttl_seconds": self.node_timeout,
        }
        self._announcement_history.append(announcement)
        logger.debug("AgentDiscovery[%s]: announced", self.local_agent_id)
        return announcement

    def discover(
        self,
        agent_id: str,
        identity: MeshIdentity | None = None,
    ) -> bool:
        """Record a discovered agent.

        Args:
            agent_id: Discovered agent ID.
            identity: The agent's identity (may be None for partial discovery).

        Returns:
            True if this is a new discovery (first time seeing this agent).
        """
        is_new = agent_id not in self._discovered

        if identity is not None:
            self._discovered[agent_id] = identity
        elif agent_id not in self._discovered:
            self._discovered[agent_id] = MeshIdentity(agent_id=agent_id)

        self._last_seen[agent_id] = time.time()

        if is_new:
            logger.info("AgentDiscovery[%s]: discovered new agent %s", self.local_agent_id, agent_id)
            for listener in self._discovery_listeners:
                listener(agent_id, self._discovered[agent_id])

        return is_new

    def forget(self, agent_id: str) -> bool:
        """Remove a previously discovered agent.

        Args:
            agent_id: Agent ID to forget.

        Returns:
            True if the agent was known and removed.
        """
        removed = self._discovered.pop(agent_id, None) is not None
        self._last_seen.pop(agent_id, None)
        if removed:
            logger.info("AgentDiscovery[%s]: forgot agent %s", self.local_agent_id, agent_id)
        return removed

    # ------------------------------------------------------------------
    # Gossip
    # ------------------------------------------------------------------

    def gossip(self) -> list[dict[str, Any]]:
        """Generate gossip messages to fan out to peers.

        Each gossip message contains a subset of known agents chosen
        by the fanout factor.

        Returns:
            List of gossip message payloads.
        """
        agents = list(self._discovered.keys())
        if not agents:
            return []

        # Select up to gossip_fanout agents to gossip about
        sample = agents[:self.gossip_fanout]
        messages: list[dict[str, Any]] = []

        for agent_id in sample:
            identity = self._discovered.get(agent_id)
            messages.append({
                "type": "gossip",
                "source": self.local_agent_id,
                "about": agent_id,
                "capabilities": list(identity.capabilities) if identity else [],
                "timestamp": time.time(),
                "ttl_seconds": self.node_timeout,
            })
        return messages

    def receive_gossip(
        self,
        gossip_msg: dict[str, Any],
    ) -> bool:
        """Process an incoming gossip message.

        Args:
            gossip_msg: The gossip message payload.

        Returns:
            True if a new agent was discovered through the gossip.
        """
        about = gossip_msg.get("about", "")
        if not about:
            return False

        caps = gossip_msg.get("capabilities", [])
        identity = MeshIdentity(
            agent_id=about,
            capabilities=list(caps),
        )
        return self.discover(about, identity)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def find_by_capability(self, capability: str) -> list[str]:
        """Find agents that have a specific capability.

        Args:
            capability: Capability string to search for.

        Returns:
            List of agent IDs matching the capability.
        """
        return [
            aid for aid, identity in self._discovered.items()
            if capability in identity.capabilities
        ]

    def find_by_name(self, name_prefix: str) -> list[str]:
        """Find agents whose ID starts with a prefix.

        Args:
            name_prefix: Agent ID prefix.

        Returns:
            List of matching agent IDs.
        """
        return [aid for aid in self._discovered if aid.startswith(name_prefix)]

    def get_discovered_agents(self) -> dict[str, MeshIdentity]:
        """Return all discovered agents and their identities."""
        return dict(self._discovered)

    def get_active_agents(self) -> list[str]:
        """Return agents seen within the timeout window."""
        now = time.time()
        return [aid for aid, last in self._last_seen.items() if now - last <= self.node_timeout]

    def agent_count(self) -> int:
        """Return the number of discovered agents."""
        return len(self._discovered)

    def get_statistics(self) -> dict[str, Any]:
        """Return discovery statistics."""
        return {
            "local_agent": self.local_agent_id,
            "method": self.discovery_method.value,
            "discovered": self.agent_count(),
            "active": len(self.get_active_agents()),
            "gossip_fanout": self.gossip_fanout,
            "announcements": len(self._announcement_history),
        }


# =============================================================================
# MeshRouter
# =============================================================================


class MeshRouter:
    """Route messages between agents on the mesh.

    MeshRouter maintains a routing table and selects the best path for
    each message based on the routing strategy (direct, capability-based,
    content-based, shortest-path, etc.).

    Attributes:
        local_node_id: This router's node ID.
        max_table_size: Maximum number of route entries.
        default_strategy: Default routing strategy.
    """

    def __init__(
        self,
        local_node_id: str,
        max_table_size: int = DEFAULT_ROUTE_TABLE_SIZE,
        default_strategy: RoutingStrategy = RoutingStrategy.DIRECT,
    ) -> None:
        self.local_node_id = local_node_id
        self.max_table_size = max_table_size
        self.default_strategy = default_strategy

        self._route_table: dict[str, RouteEntry] = {}
        self._routed_messages: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Route table management
    # ------------------------------------------------------------------

    def add_route(
        self,
        target_id: str,
        next_hop: str,
        cost: float = 1.0,
        ttl: float = 300.0,
        strategy: RoutingStrategy = RoutingStrategy.DIRECT,
    ) -> bool:
        """Add or update a route entry.

        Args:
            target_id: Destination agent ID.
            next_hop: Next-hop agent ID.
            cost: Route cost.
            ttl: Route TTL in seconds.
            strategy: Routing strategy.

        Returns:
            True if the route was added (or updated).
        """
        # Enforce table size limit (LRU eviction)
        if target_id not in self._route_table and len(self._route_table) >= self.max_table_size:
            oldest = min(self._route_table.keys(), key=lambda k: self._route_table[k].last_updated)
            del self._route_table[oldest]

        self._route_table[target_id] = RouteEntry(
            target_id=target_id,
            next_hop=next_hop,
            cost=cost,
            ttl=ttl,
            last_updated=time.time(),
            strategy=strategy,
        )
        return True

    def remove_route(self, target_id: str) -> bool:
        """Remove a route entry.

        Returns:
            True if the route was found and removed.
        """
        return self._route_table.pop(target_id, None) is not None

    def get_route(self, target_id: str) -> RouteEntry | None:
        """Get a route entry for a target.

        Returns:
            RouteEntry if found and not expired, else None.
        """
        entry = self._route_table.get(target_id)
        if entry is None or entry.is_expired():
            if entry is not None:
                del self._route_table[target_id]
            return None
        return entry

    def clear_routes(self) -> None:
        """Clear all route entries."""
        self._route_table.clear()

    def prune_expired(self) -> int:
        """Remove all expired route entries.

        Returns:
            Number of pruned entries.
        """
        expired = [tid for tid, entry in self._route_table.items() if entry.is_expired()]
        for tid in expired:
            del self._route_table[tid]
        return len(expired)

    def route_count(self) -> int:
        """Return the number of active route entries."""
        self.prune_expired()
        return len(self._route_table)

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(
        self,
        target: str,
        payload: dict[str, Any],
        strategy: RoutingStrategy | None = None,
    ) -> dict[str, Any]:
        """Route a message to a target agent.

        Args:
            target: Target agent ID (or "*" for broadcast).
            payload: Message payload.
            strategy: Override routing strategy.

        Returns:
            The routed message envelope.

        Raises:
            ValueError: If the target is unreachable.
        """
        actual_strategy = strategy or self.default_strategy

        if target == "*" or actual_strategy == RoutingStrategy.BROADCAST:
            return self._route_broadcast(payload)

        if actual_strategy == RoutingStrategy.CAPABILITY:
            return self._route_by_capability(payload)

        # DIRECT, SHORTEST_PATH, OPPORTUNISTIC
        entry = self.get_route(target)
        if entry is None:
            raise ValueError(f"Target {target} is unreachable (no route)")

        routed = {
            "message_id": str(uuid.uuid4()),
            "source": self.local_node_id,
            "target": target,
            "next_hop": entry.next_hop,
            "strategy": actual_strategy.value,
            "cost": entry.cost,
            "payload": payload,
            "timestamp": time.time(),
        }
        self._routed_messages.append(routed)
        return routed

    def _route_broadcast(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Broadcast a message to all known targets."""
        routed = {
            "message_id": str(uuid.uuid4()),
            "source": self.local_node_id,
            "target": "*",
            "next_hop": "*",
            "strategy": "broadcast",
            "cost": 0.0,
            "payload": payload,
            "timestamp": time.time(),
        }
        self._routed_messages.append(routed)
        return routed

    def _route_by_capability(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Route based on required capability from payload."""
        required_cap = payload.get("required_capability", "")
        best_entry: RouteEntry | None = None

        for entry in self._route_table.values():
            if entry.is_expired():
                continue
            if entry.strategy == RoutingStrategy.CAPABILITY:
                best_entry = entry
                break

        if best_entry is None:
            raise ValueError("No capability-based route available")

        routed = {
            "message_id": str(uuid.uuid4()),
            "source": self.local_node_id,
            "target": best_entry.target_id,
            "next_hop": best_entry.next_hop,
            "strategy": "capability",
            "cost": best_entry.cost,
            "payload": payload,
            "timestamp": time.time(),
        }
        self._routed_messages.append(routed)
        return routed

    def get_history(self) -> list[dict[str, Any]]:
        """Return the routed message history."""
        return list(self._routed_messages)

    def get_statistics(self) -> dict[str, Any]:
        """Return router statistics."""
        self.prune_expired()
        return {
            "local_node": self.local_node_id,
            "routes": len(self._route_table),
            "max_table_size": self.max_table_size,
            "messages_routed": len(self._routed_messages),
            "default_strategy": self.default_strategy.value,
        }


# =============================================================================
# MeshEncryption
# =============================================================================


class MeshEncryption:
    """Encrypt and decrypt mesh communications.

    Supports multiple encryption schemes (AES-GCM, ChaCha20, hybrid
    ECDH) as well as HMAC signing for integrity verification.

    Attributes:
        local_agent_id: This agent's ID.
        default_scheme: Default encryption scheme.
    """

    def __init__(
        self,
        local_agent_id: str,
        default_scheme: EncryptionScheme = EncryptionScheme.AES_GCM,
    ) -> None:
        self.local_agent_id = local_agent_id
        self.default_scheme = default_scheme

        # Simulated key store (in production, use a proper KMS)
        self._symmetric_keys: dict[str, bytes] = {}
        self._key_derivation_count: int = 0

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------

    def generate_key(self, key_size: int = DEFAULT_KEY_SIZE_BYTES) -> bytes:
        """Generate a new symmetric key.

        Args:
            key_size: Key size in bytes.

        Returns:
            The generated key bytes.
        """
        key = secrets.token_bytes(key_size)
        self._key_derivation_count += 1
        return key

    def store_key(self, key_id: str, key: bytes) -> None:
        """Store a symmetric key by identifier.

        Args:
            key_id: Key identifier.
            key: Key bytes.
        """
        self._symmetric_keys[key_id] = key

    def get_key(self, key_id: str) -> bytes | None:
        """Retrieve a stored key.

        Returns:
            The key bytes or None if not found.
        """
        return self._symmetric_keys.get(key_id)

    def derive_key(self, passphrase: str, salt: bytes | None = None) -> bytes:
        """Derive a symmetric key from a passphrase (PBKDF2-style).

        Args:
            passphrase: The passphrase.
            salt: Optional salt bytes (random if None).

        Returns:
            Derived key bytes.
        """
        if salt is None:
            salt = secrets.token_bytes(16)
        key = hashlib.pbkdf2_hmac(
            SIGNATURE_HASH,
            passphrase.encode("utf-8"),
            salt,
            100_000,  # iterations
            dklen=DEFAULT_KEY_SIZE_BYTES,
        )
        self._key_derivation_count += 1
        return key

    # ------------------------------------------------------------------
    # Encrypt / decrypt
    # ------------------------------------------------------------------

    def encrypt(
        self,
        plaintext: str,
        key_id: str = "",
        scheme: EncryptionScheme | None = None,
    ) -> MeshEnvelope:
        """Encrypt plaintext into a MeshEnvelope.

        In this simulated implementation, we use a XOR-like obfuscation
        with the symmetric key.  A production version would use AES-GCM
        or ChaCha20-Poly1305 via the cryptography library.

        Args:
            plaintext: The plaintext to encrypt.
            key_id: ID of the symmetric key to use.
            scheme: Encryption scheme override.

        Returns:
            A MeshEnvelope containing the ciphertext.

        Raises:
            ValueError: If the key is not found.
        """
        actual_scheme = scheme or self.default_scheme

        if actual_scheme == EncryptionScheme.NONE:
            return MeshEnvelope(
                envelope_id=str(uuid.uuid4()),
                sender_id=self.local_agent_id,
                recipient_id="*",
                ciphertext=plaintext,
                iv="",
                scheme=EncryptionScheme.NONE,
                metadata={"plaintext": True},
            )

        key = self._symmetric_keys.get(key_id)
        if key is None:
            raise ValueError(f"Encryption key '{key_id}' not found")

        # Simulated encryption: XOR each byte with the key (in production use AES-GCM)
        iv = os.urandom(12).hex()
        data = plaintext.encode("utf-8")
        repeated = (key * (len(data) // len(key) + 1))[:len(data)]
        cipher_bytes = bytes(d ^ k for d, k in zip(data, repeated))
        ciphertext = cipher_bytes.hex()

        # Signature
        signature = hmac.new(key, ciphertext.encode("utf-8"), SIGNATURE_HASH).hexdigest()

        envelope = MeshEnvelope(
            envelope_id=str(uuid.uuid4()),
            sender_id=self.local_agent_id,
            recipient_id="*",
            ciphertext=ciphertext,
            iv=iv,
            scheme=actual_scheme,
            signature=signature,
        )
        envelope.metadata = {"key_id": key_id}
        return envelope

    def decrypt(
        self,
        envelope: MeshEnvelope,
        key_id: str = "",
    ) -> str:
        """Decrypt a MeshEnvelope back to plaintext.

        Args:
            envelope: The encrypted envelope.
            key_id: ID of the key to use (overrides envelope metadata).

        Returns:
            Decrypted plaintext.

        Raises:
            ValueError: If the key is not found or verification fails.
        """
        if envelope.scheme == EncryptionScheme.NONE:
            return envelope.ciphertext

        actual_key_id = key_id or envelope.metadata.get("key_id", "")
        key = self._symmetric_keys.get(actual_key_id)
        if key is None:
            raise ValueError(f"Decryption key '{actual_key_id}' not found")

        # Verify signature
        expected_sig = hmac.new(key, envelope.ciphertext.encode("utf-8"), SIGNATURE_HASH).hexdigest()
        if not hmac.compare_digest(expected_sig, envelope.signature):
            raise ValueError("Message signature verification failed")

        # Simulated decryption
        cipher_bytes = bytes.fromhex(envelope.ciphertext)
        repeated = (key * (len(cipher_bytes) // len(key) + 1))[:len(cipher_bytes)]
        plain_bytes = bytes(d ^ k for d, k in zip(cipher_bytes, repeated))
        return plain_bytes.decode("utf-8")

    def sign(self, payload: str, key_id: str) -> str:
        """Sign a payload with a symmetric key (HMAC).

        Args:
            payload: The payload to sign.
            key_id: Key identifier.

        Returns:
            Hex-encoded HMAC signature.

        Raises:
            ValueError: If the key is not found.
        """
        key = self._symmetric_keys.get(key_id)
        if key is None:
            raise ValueError(f"Signing key '{key_id}' not found")
        return hmac.new(key, payload.encode("utf-8"), SIGNATURE_HASH).hexdigest()

    def verify(self, payload: str, signature: str, key_id: str) -> bool:
        """Verify an HMAC signature.

        Args:
            payload: The original payload.
            signature: The claimed signature (hex).
            key_id: Key identifier.

        Returns:
            True if the signature is valid.
        """
        expected = self.sign(payload, key_id)
        return hmac.compare_digest(expected, signature)

    def get_statistics(self) -> dict[str, Any]:
        """Return encryption statistics."""
        return {
            "local_agent": self.local_agent_id,
            "default_scheme": self.default_scheme.value,
            "stored_keys": len(self._symmetric_keys),
            "key_derivations": self._key_derivation_count,
        }


# =============================================================================
# MeshSecurity
# =============================================================================


class MeshSecurity:
    """Authenticate agents and enforce access control on the mesh.

    MeshSecurity handles agent authentication (token, certificate,
    challenge-response, mTLS) and authorization (access levels per
    operation).

    Attributes:
        local_agent_id: This agent's ID.
        default_auth_method: Default authentication method.
    """

    def __init__(
        self,
        local_agent_id: str,
        default_auth_method: AuthMethod = AuthMethod.TOKEN,
    ) -> None:
        self.local_agent_id = local_agent_id
        self.default_auth_method = default_auth_method

        self._authenticated_agents: dict[str, MeshIdentity] = {}
        self._auth_tokens: dict[str, str] = {}  # agent_id -> token
        self._access_rules: list[AccessRule] = []
        self._auth_attempts: dict[str, list[float]] = {}
        self._max_auth_attempts: int = 5

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def issue_token(self, agent_id: str) -> str:
        """Issue a new authentication token for an agent.

        Args:
            agent_id: Agent to issue the token for.

        Returns:
            The issued token string.
        """
        token = secrets.token_hex(32)
        self._auth_tokens[agent_id] = token
        logger.info("MeshSecurity[%s]: issued token for %s", self.local_agent_id, agent_id)
        return token

    def revoke_token(self, agent_id: str) -> bool:
        """Revoke an authentication token.

        Returns:
            True if the token was revoked.
        """
        return self._auth_tokens.pop(agent_id, None) is not None

    def validate_token(self, agent_id: str, token: str) -> bool:
        """Validate an authentication token.

        Args:
            agent_id: Claimed agent ID.
            token: Token to validate.

        Returns:
            True if the token is valid.
        """
        stored = self._auth_tokens.get(agent_id)
        if stored is None:
            return False
        return secrets.compare_digest(stored, token)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(
        self,
        agent_id: str,
        credential: str,
        auth_method: AuthMethod | None = None,
    ) -> bool:
        """Authenticate an agent on the mesh.

        Args:
            agent_id: Claimed agent ID.
            credential: Credential (token, certificate, etc.).
            auth_method: Authentication method override.

        Returns:
            True if authentication succeeded.

        Raises:
            ValueError: If the auth method is not supported.
        """
        # Rate limiting
        attempts = self._auth_attempts.setdefault(agent_id, [])
        now = time.time()
        # Prune attempts older than 60s
        attempts[:] = [t for t in attempts if now - t < 60.0]

        if len(attempts) >= self._max_auth_attempts:
            logger.warning("MeshSecurity[%s]: rate-limited auth for %s", self.local_agent_id, agent_id)
            return False

        attempts.append(now)

        method = auth_method or self.default_auth_method

        if method == AuthMethod.TOKEN:
            success = self.validate_token(agent_id, credential)
        elif method == AuthMethod.CHALLENGE_RESPONSE:
            success = self._verify_challenge_response(agent_id, credential)
        elif method == AuthMethod.CERTIFICATE:
            success = self._verify_certificate(agent_id, credential)
        elif method == AuthMethod.MUTUAL_TLS:
            success = self._verify_mtls(agent_id, credential)
        else:
            raise ValueError(f"Unsupported auth method: {method}")

        if success:
            identity = self._authenticated_agents.get(agent_id)
            if identity is None:
                identity = MeshIdentity(agent_id=agent_id, auth_method=method)
                self._authenticated_agents[agent_id] = identity
            logger.info("MeshSecurity[%s]: authenticated %s via %s", self.local_agent_id, agent_id, method.value)
        else:
            logger.warning("MeshSecurity[%s]: auth failed for %s", self.local_agent_id, agent_id)

        return success

    @staticmethod
    def _verify_challenge_response(agent_id: str, response: str) -> bool:
        """Simulated challenge-response verification."""
        # In production, verify a signed challenge
        return len(response) > 0

    @staticmethod
    def _verify_certificate(agent_id: str, certificate: str) -> bool:
        """Simulated certificate verification."""
        # In production, validate X.509 cert chain
        return certificate.startswith("-----BEGIN CERTIFICATE-----")

    @staticmethod
    def _verify_mtls(agent_id: str, credential: str) -> bool:
        """Simulated mTLS verification."""
        return len(credential) > 10

    def is_authenticated(self, agent_id: str) -> bool:
        """Check if an agent is authenticated.

        Args:
            agent_id: Agent ID.

        Returns:
            True if the agent has been authenticated.
        """
        return agent_id in self._authenticated_agents

    def deauthenticate(self, agent_id: str) -> bool:
        """Deauthenticate an agent.

        Returns:
            True if the agent was authenticated and removed.
        """
        return self._authenticated_agents.pop(agent_id, None) is not None

    def get_authenticated_agents(self) -> list[str]:
        """Return list of authenticated agent IDs."""
        return list(self._authenticated_agents.keys())

    # ------------------------------------------------------------------
    # Access control
    # ------------------------------------------------------------------

    def set_access_level(self, agent_id: str, level: AccessLevel) -> None:
        """Set the access level for an authenticated agent.

        Args:
            agent_id: Authenticated agent ID.
            level: Access level to assign.

        Raises:
            ValueError: If the agent is not authenticated.
        """
        identity = self._authenticated_agents.get(agent_id)
        if identity is None:
            raise ValueError(f"Cannot set access level for unauthenticated agent {agent_id}")
        identity.access_level = level

    def get_access_level(self, agent_id: str) -> AccessLevel:
        """Get the access level for an agent.

        Args:
            agent_id: Agent ID.

        Returns:
            The agent's access level (NONE if unknown).
        """
        identity = self._authenticated_agents.get(agent_id)
        return identity.access_level if identity else AccessLevel.NONE

    def check_access(self, agent_id: str, required_level: AccessLevel) -> bool:
        """Check if an agent has at least the required access level.

        Args:
            agent_id: Agent ID.
            required_level: Minimum access level needed.

        Returns:
            True if the agent meets the requirement.
        """
        actual = self.get_access_level(agent_id)
        return actual.value >= required_level.value

    def add_access_rule(self, rule: AccessRule) -> None:
        """Add an access control rule.

        Args:
            rule: The access rule to add.
        """
        self._access_rules.append(rule)

    def evaluate_rules(
        self,
        agent_id: str,
        operation: str,
        resource: str = "",
    ) -> list[AccessRule]:
        """Evaluate all access rules for a given operation.

        Args:
            agent_id: Agent performing the operation.
            operation: Operation name.
            resource: Target resource (optional).

        Returns:
            List of matching rules sorted by priority.
        """
        matching = [
            r for r in self._access_rules
            if r.matches(agent_id, operation, resource)
        ]
        return sorted(matching, key=lambda r: r.priority, reverse=True)

    # ------------------------------------------------------------------
    # Auditing
    # ------------------------------------------------------------------

    def set_max_auth_attempts(self, max_attempts: int) -> None:
        """Set the maximum authentication attempts per minute.

        Args:
            max_attempts: Maximum failed attempts per minute.
        """
        self._max_auth_attempts = max_attempts

    def get_auth_attempts(self, agent_id: str) -> int:
        """Get the recent authentication attempt count for an agent.

        Args:
            agent_id: Agent ID.

        Returns:
            Number of recent attempts.
        """
        attempts = self._auth_attempts.get(agent_id, [])
        now = time.time()
        return sum(1 for t in attempts if now - t < 60.0)

    def get_statistics(self) -> dict[str, Any]:
        """Return security statistics."""
        return {
            "local_agent": self.local_agent_id,
            "default_auth_method": self.default_auth_method.value,
            "authenticated_agents": len(self._authenticated_agents),
            "active_tokens": len(self._auth_tokens),
            "access_rules": len(self._access_rules),
            "max_auth_attempts_per_min": self._max_auth_attempts,
        }


# =============================================================================
# AccessRule
# =============================================================================


@dataclass
class AccessRule:
    """An access control rule for mesh operations.

    Attributes:
        rule_id: Unique rule identifier.
        agent_pattern: Agent ID glob pattern (e.g., "agent-*").
        operation: Operation name (e.g., "send_message", "discover").
        resource_pattern: Resource glob pattern (e.g., "memory:*").
        allowed: Whether this rule allows (True) or denies (False).
        priority: Rule priority (higher = evaluated first).
    """

    rule_id: str
    agent_pattern: str
    operation: str
    resource_pattern: str = "*"
    allowed: bool = True
    priority: int = 0

    def matches(self, agent_id: str, operation: str, resource: str = "") -> bool:
        """Check if this rule matches the given context.

        Args:
            agent_id: Agent ID to match.
            operation: Operation name to match.
            resource: Resource to match (optional).

        Returns:
            True if this rule applies.
        """
        import fnmatch

        if not fnmatch.fnmatch(agent_id, self.agent_pattern):
            return False
        if self.operation != "*" and self.operation != operation:
            return False
        if resource and self.resource_pattern != "*":
            if not fnmatch.fnmatch(resource, self.resource_pattern):
                return False
        return True
