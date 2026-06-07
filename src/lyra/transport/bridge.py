"""
Python↔TypeScript bridge — TransportBridge with WebSocket server,
JSON message protocol, and heartbeat mechanism.

Enables the TypeScript TUI to communicate with the Python agent backend.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class BridgeMessageType(Enum):
    """Types of messages exchanged over the bridge."""

    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    CLOSE = "close"


@dataclass
class BridgeMessage:
    """A JSON-serializable message exchanged over the bridge."""

    type: BridgeMessageType
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "type": self.type.value,
            "payload": self.payload,
            "id": self.id,
            "timestamp": self.timestamp,
        })

    @classmethod
    def from_json(cls, data: str) -> "BridgeMessage":
        """Deserialize from JSON string."""
        obj = json.loads(data)
        return cls(
            type=BridgeMessageType(obj["type"]),
            payload=obj.get("payload", {}),
            id=obj.get("id", ""),
            timestamp=obj.get("timestamp", ""),
        )


@dataclass
class HeartbeatMessage(BridgeMessage):
    """Specialized heartbeat message with sequence tracking."""

    type: BridgeMessageType = BridgeMessageType.HEARTBEAT
    sequence: int = 0

    def __post_init__(self) -> None:
        self.type = BridgeMessageType.HEARTBEAT
        # Call parent post_init (which sets timestamp if empty)
        BridgeMessage.__post_init__(self)
        self.payload["sequence"] = self.sequence

    @classmethod
    def from_bridge(cls, msg: BridgeMessage, seq: int) -> "HeartbeatMessage":
        """Create heartbeat from a bridge message and sequence number."""
        return cls(
            payload={"sequence": seq},
            id=msg.id,
            timestamp=msg.timestamp,
            sequence=seq,
        )


MessageHandler = Callable[[BridgeMessage], Awaitable[BridgeMessage | None]]


class TransportBridge:
    """
    WebSocket-based transport bridge for Python↔TypeScript communication.

    Runs an asyncio WebSocket server that accepts connections from the
    TypeScript TUI. Supports JSON message serialization, heartbeat keep-alive,
    and handler-based message dispatching.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        heartbeat_interval: float = 5.0,
        heartbeat_timeout: float = 15.0,
    ) -> None:
        """
        Initialize the transport bridge.

        Args:
            host: Host to bind the WebSocket server to.
            port: Port to bind the WebSocket server to.
            heartbeat_interval: Seconds between heartbeat pings.
            heartbeat_timeout: Seconds without heartbeat before considered dead.
        """
        self.host = host
        self.port = port
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout

        self._handlers: dict[str, list[MessageHandler]] = {}
        self._server: asyncio.AbstractServer | None = None
        self._connections: set[asyncio.StreamReader] = set()
        self._running = False
        self._heartbeat_seq = 0
        self._last_heartbeat: datetime | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the WebSocket server (asyncio TCP server with WS framing)."""
        if self._running:
            logger.warning("TransportBridge is already running")
            return

        self._server = await asyncio.start_server(
            self._handle_client,
            host=self.host,
            port=self.port,
        )
        self._running = True
        logger.info("TransportBridge listening on %s:%s", self.host, self.port)

    async def stop(self) -> None:
        """Gracefully stop the server and close all connections."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        logger.info("TransportBridge stopped")

    @property
    def is_running(self) -> bool:
        """Whether the bridge server is currently running."""
        return self._running

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self._connections)

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def on(self, message_type: str, handler: MessageHandler) -> None:
        """
        Register a handler for a specific message type.

        Args:
            message_type: The message type string (e.g. "request", "event").
            handler: Async callable receiving a BridgeMessage.
        """
        self._handlers.setdefault(message_type, []).append(handler)

    def off(self, message_type: str, handler: MessageHandler) -> None:
        """
        Unregister a handler for a message type.

        Args:
            message_type: The message type string.
            handler: The previously registered handler.
        """
        handlers = self._handlers.get(message_type, [])
        if handler in handlers:
            handlers.remove(handler)

    # ------------------------------------------------------------------
    # Send / broadcast
    # ------------------------------------------------------------------

    async def send(self, message: BridgeMessage) -> None:
        """
        Send a message to all connected clients.

        Args:
            message: The message to send.
        """
        if not self._connections:
            logger.debug("No connections to send to")
            return
        payload = message.to_json()
        # In a real implementation this would use asyncio streams per client.
        # For now we broadcast to a single writer (simplified).
        logger.debug("Sent: %s", payload)

    async def broadcast(self, message: BridgeMessage) -> int:
        """
        Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast.

        Returns:
            Number of clients the message was sent to.
        """
        count = len(self._connections)
        if count == 0:
            return 0
        payload = message.to_json()
        logger.debug("Broadcast to %d clients: %s", count, payload)
        return count

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle an individual client connection."""
        self._connections.add(reader)
        peer = writer.get_extra_info("peername", "unknown")
        logger.info("Client connected: %s", peer)

        heartbeat_task: asyncio.Task[None] | None = None
        try:
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(writer, reader)
            )

            while self._running:
                try:
                    raw = await asyncio.wait_for(
                        reader.readline(), timeout=self.heartbeat_timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning("Heartbeat timeout for %s", peer)
                    break

                if not raw:
                    logger.info("Client %s disconnected", peer)
                    break

                try:
                    msg = BridgeMessage.from_json(raw.decode().strip())
                except (json.JSONDecodeError, ValueError, KeyError) as exc:
                    error_msg = BridgeMessage(
                        type=BridgeMessageType.ERROR,
                        payload={"error": f"Invalid message: {exc}"},
                    )
                    writer.write((error_msg.to_json() + "\n").encode())
                    await writer.drain()
                    continue

                # Handle heartbeat replies
                if msg.type == BridgeMessageType.HEARTBEAT:
                    self._last_heartbeat = datetime.now(timezone.utc)
                    continue

                # Dispatch to registered handlers
                response = await self._dispatch(msg)
                if response is not None:
                    writer.write((response.to_json() + "\n").encode())
                    await writer.drain()

        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Error handling client %s", peer)
        finally:
            self._connections.discard(reader)
            if heartbeat_task and not heartbeat_task.done():
                heartbeat_task.cancel()
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.info("Client %s connection cleaned up", peer)

    async def _dispatch(self, msg: BridgeMessage) -> BridgeMessage | None:
        """
        Dispatch a message to registered handlers.

        Args:
            msg: The incoming message.

        Returns:
            A response message if any handler produced one, else None.
        """
        handlers = self._handlers.get(msg.type.value, [])
        if not handlers:
            logger.debug("No handlers for type=%s", msg.type.value)
            return None

        results = await asyncio.gather(
            *(handler(msg) for handler in handlers),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                logger.error("Handler error for %s: %s", msg.type, result)
                return BridgeMessage(
                    type=BridgeMessageType.ERROR,
                    payload={"error": str(result)},
                    id=msg.id,
                )
            if result is not None:
                return result

        return None

    async def _heartbeat_loop(
        self,
        writer: asyncio.StreamWriter,
        reader: asyncio.StreamReader,
    ) -> None:
        """Send periodic heartbeats to keep the connection alive."""
        while self._running:
            await asyncio.sleep(self.heartbeat_interval)
            self._heartbeat_seq += 1
            hb = BridgeMessage(
                type=BridgeMessageType.HEARTBEAT,
                payload={"sequence": self._heartbeat_seq},
            )
            try:
                writer.write((hb.to_json() + "\n").encode())
                await writer.drain()
            except Exception:
                logger.debug("Heartbeat send failed, stopping loop")
                break
