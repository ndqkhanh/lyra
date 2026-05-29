"""
Async WebSocket server for AG-UI protocol delivery.

Supports:
  - Multi-device session fan-out
  - per-message compression (permessage-deflate) readiness
  - Graceful shutdown
  - Connection metrics
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from lyra_streaming.models import AGEvent, EventType
from lyra_streaming.protocol import AGUIProtocol
from lyra_streaming.session import SessionManager

logger = logging.getLogger(__name__)


class ConnectionMetrics:
    """Aggregated per-server connection statistics."""

    def __init__(self) -> None:
        self.total_connections: int = 0
        self.active_connections: int = 0
        self.total_events_sent: int = 0
        self.total_events_received: int = 0
        self.total_errors: int = 0
        self.started_at: datetime = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "total_events_sent": self.total_events_sent,
            "total_events_received": self.total_events_received,
            "total_errors": self.total_errors,
            "uptime_seconds": (datetime.now(timezone.utc) - self.started_at).total_seconds(),
        }


class WebSocketServer:
    """Async WebSocket server for the AG-UI protocol.

    Integrates with `SessionManager` to support multi-device fan-out and
    durable sessions.

    Usage::

        server = WebSocketServer(session_manager=sm)
        await server.start("0.0.0.0", 8765)
        ...
        await server.stop()
    """

    def __init__(self, session_manager: SessionManager | None = None) -> None:
        self._session_manager = session_manager or SessionManager()
        self._protocol = AGUIProtocol()
        self._server: asyncio.AbstractServer | None = None
        self._connections: set[Any] = set()
        self.metrics = ConnectionMetrics()

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

    async def start(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        """Start the WebSocket server on *host*:*port*.

        Args:
            host: Bind address.
            port: Bind port.
        """
        self._server = await asyncio.start_server(
            self._handle_connection,
            host=host,
            port=port,
        )
        logger.info("WebSocket server listening on %s:%d", host, port)

    async def stop(self) -> None:
        """Gracefully shut down the WebSocket server.

        Closes all active connections before stopping the server socket.
        """
        logger.info("Shutting down WebSocket server...")

        # Close all active connections
        for ws in list(self._connections):
            try:
                await ws.close()
            except Exception:
                pass
        self._connections.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        self.metrics.active_connections = 0
        logger.info("WebSocket server stopped")

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a raw TCP connection (used for lightweight testing).

        In production the caller should use the ``websockets`` library
        and call `handle_connection` directly.  This raw handler uses
        a simple line-delimited JSON protocol for testability.

        For full WebSocket support, install ``websockets>=12.0`` and
        use the `handle_websocket` method.
        """
        self.metrics.total_connections += 1
        self.metrics.active_connections += 1

        addr = writer.get_extra_info("peername", "unknown")
        logger.debug("Connection from %s", addr)

        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                self.metrics.total_events_received += 1
                raw = line.strip()
                if not raw:
                    continue

                try:
                    event_type = self._protocol.get_event_type(raw)
                    event = self._protocol.decode(raw)
                    logger.debug("Received event type=%s", event_type.name)

                    # Echo back for testing; production handlers inject here
                    ack_event = AGEvent(
                        type=EventType.RAW,
                        run_id=event.run_id,
                        sequence_number=event.sequence_number + 1,
                    )
                    await self._send_raw(writer, ack_event)
                except Exception:
                    self.metrics.total_errors += 1
                    logger.exception("Error handling raw connection event")

        except asyncio.CancelledError:
            pass
        except Exception:
            self.metrics.total_errors += 1
            logger.exception("Connection error from %s", addr)
        finally:
            self.metrics.active_connections -= 1
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _send_raw(self, writer: asyncio.StreamWriter, event: AGEvent) -> None:
        """Send an event over a raw TCP connection (line-delimited JSON)."""
        encoded = self._protocol.encode(event) + b"\n"
        writer.write(encoded)
        await writer.drain()
        self.metrics.total_events_sent += 1

    async def send_event(self, writer: asyncio.StreamWriter, event: AGEvent) -> None:
        """Encode and send an AG-UI event over a writer.

        Args:
            writer: The connection writer (TCP or WebSocket).
            event: The event to send.
        """
        await self._send_raw(writer, event)

    async def broadcast_event(self, event: AGEvent, session_id: str) -> list[str]:
        """Queue an event for broadcast to all devices in *session_id*.

        Returns the list of device IDs that should receive the event.
        The caller is responsible for the actual per-device send.
        """
        return self._session_manager.broadcast(session_id, event)

    def get_connection_stats(self) -> dict[str, Any]:
        """Return current connection metrics as a dict."""
        return self.metrics.to_dict()

    # ── WebSocket integration (requires ``websockets`` library) ────

    async def handle_websocket(self, websocket: Any) -> None:
        """Handle a single WebSocket connection (for use with the
        ``websockets`` library).

        Call this from ``websockets.serve(self.handle_websocket, host, port)``.

        Args:
            websocket: A ``websockets.WebSocketServerProtocol`` instance.
        """
        self.metrics.total_connections += 1
        self.metrics.active_connections += 1

        try:
            async for message in websocket:
                self.metrics.total_events_received += 1

                if isinstance(message, bytes):
                    raw = message
                else:
                    raw = message.encode("utf-8")

                try:
                    event = self._protocol.decode(raw)
                    logger.debug("WebSocket received event type=%s", event.type.name)

                    # Echo the event back for protocol-level testing
                    response = self._protocol.encode(event)
                    await websocket.send(response)
                    self.metrics.total_events_sent += 1
                except Exception:
                    self.metrics.total_errors += 1
                    logger.exception("Error handling WebSocket message")

        except Exception:
            self.metrics.total_errors += 1
            logger.exception("WebSocket connection error")
        finally:
            self.metrics.active_connections -= 1
