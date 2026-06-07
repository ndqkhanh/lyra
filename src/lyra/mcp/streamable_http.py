"""
StreamableHTTPTransport — SSE-based streaming transport for MCP.

Implements a streaming HTTP transport using Server-Sent Events (SSE)
for real-time tool progress updates, with auto-reconnect via exponential
backoff and connection pooling for multiple MCP servers.

Key features
------------
- SSE-based streaming: Tool progress updates are pushed to the client
  as Server-Sent Events, enabling real-time progress visibility.
- AutoReconnect: Automatic reconnection with exponential backoff when
  the connection drops (base delay 1s, max 60s, jitter).
- Connection pooling: Manages connections to multiple MCP servers,
  reusing connections where possible and enforcing limits.

References
----------
- MCP Streamable HTTP Specification (SEP-1442)
  https://spec.modelcontextprotocol.io
- Server-Sent Events (W3C)
  https://html.spec.whatwg.org/multipage/server-sent-events.html
"""

from __future__ import annotations

import asyncio
import json
import math
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# -- types ------------------------------------------------------------------
# ---------------------------------------------------------------------------


class SSEEventType(Enum):
    """Server-Sent Event types for MCP streaming."""

    TOOL_START = "tool_start"
    TOOL_PROGRESS = "tool_progress"
    TOOL_COMPLETE = "tool_complete"
    TOOL_ERROR = "tool_error"
    CONNECTION_STATUS = "connection_status"
    HEARTBEAT = "heartbeat"


@dataclass(frozen=True)
class SSEEvent:
    """A single Server-Sent Event for MCP streaming.

    Attributes:
        event_type: The SSE event type.
        data: Event payload as a JSON-compatible dict.
        event_id: Optional event ID for replay / tracking.
        timestamp: Unix timestamp when the event was created.
        server_id: Optional server identifier.
    """

    event_type: SSEEventType
    data: dict[str, Any] = field(default_factory=dict)
    event_id: str = ""
    timestamp: float = 0.0
    server_id: str = ""

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            object.__setattr__(self, "timestamp", time.time())
        if not self.event_id:
            object.__setattr__(
                self,
                "event_id",
                f"{self.event_type.value}_{int(self.timestamp * 1000)}",
            )

    def serialize(self) -> str:
        """Serialize this event to SSE wire format.

        Returns:
            A string conforming to the SSE protocol:
                ``event: <type>\\ndata: <json>\\n\\n``
        """
        lines = [
            f"event: {self.event_type.value}",
            f"id: {self.event_id}",
            f"data: {json.dumps(self.data, default=str)}",
            "",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# -- Connection pool --------------------------------------------------------
# ---------------------------------------------------------------------------


@dataclass
class PoolConfig:
    """Configuration for the MCP connection pool.

    Attributes:
        max_connections: Maximum concurrent connections per server.
        max_total_connections: Maximum total connections across all servers.
        connection_timeout_s: Connection timeout in seconds.
        idle_timeout_s: Idle connection timeout before recycling.
        health_check_interval_s: How often to health-check pooled connections.
    """

    max_connections: int = 5
    max_total_connections: int = 20
    connection_timeout_s: float = 10.0
    idle_timeout_s: float = 60.0
    health_check_interval_s: float = 30.0


@dataclass
class Connection:
    """A pooled connection to an MCP server.

    Attributes:
        server_id: Server identifier.
        url: Server URL.
        connected_at: Timestamp when the connection was established.
        last_used_at: Timestamp of last use.
        is_healthy: Whether the connection is healthy.
        error_count: Number of consecutive errors.
    """

    server_id: str = ""
    url: str = ""
    connected_at: float = 0.0
    last_used_at: float = 0.0
    is_healthy: bool = True
    error_count: int = 0

    @property
    def is_idle(self) -> bool:
        """Whether the connection is idle (exceeded idle_timeout)."""
        return time.time() - self.last_used_at > 60.0


class ConnectionPool:
    """Pool of connections to MCP servers.

    Manages the lifecycle of HTTP connections to multiple MCP servers,
    enforcing connection limits and recycling idle connections.
    """

    def __init__(self, config: PoolConfig | None = None) -> None:
        self._config = config or PoolConfig()
        self._connections: dict[str, list[Connection]] = {}
        self._total_count: int = 0

    def acquire(self, server_id: str, url: str) -> Connection:
        """Acquire a connection from the pool or create a new one.

        Args:
            server_id: Server identifier.
            url: Server URL for new connections.

        Returns:
            A ``Connection``.

        Raises:
            RuntimeError: If max connections exceeded.
        """
        # Check total limit
        if self._total_count >= self._config.max_total_connections:
            # Try to recycle an idle connection
            self._recycle_idle()

        if self._total_count >= self._config.max_total_connections:
            raise RuntimeError(
                f"Max total connections ({self._config.max_total_connections}) reached",
            )

        # Check per-server limit
        server_conns = self._connections.get(server_id, [])
        if len(server_conns) >= self._config.max_connections:
            # Try to recycle an idle one for this server
            for conn in server_conns:
                if conn.is_idle:
                    server_conns.remove(conn)
                    self._total_count -= 1
                    break
            else:
                raise RuntimeError(
                    f"Max connections ({self._config.max_connections}) "
                    f"reached for server '{server_id}'",
                )

        # Create new connection
        conn = Connection(
            server_id=server_id,
            url=url,
            connected_at=time.time(),
            last_used_at=time.time(),
            is_healthy=True,
        )

        self._connections.setdefault(server_id, []).append(conn)
        self._total_count += 1
        return conn

    def release(self, conn: Connection) -> None:
        """Release a connection back to the pool.

        Args:
            conn: The connection to release.
        """
        conn.last_used_at = time.time()

    def remove(self, conn: Connection) -> None:
        """Remove a connection from the pool (e.g., on error).

        Args:
            conn: The connection to remove.
        """
        server_conns = self._connections.get(conn.server_id, [])
        if conn in server_conns:
            server_conns.remove(conn)
            self._total_count -= 1
            logger.debug("connection removed from pool", server_id=conn.server_id)

    def mark_unhealthy(self, conn: Connection) -> None:
        """Mark a connection as unhealthy.

        Args:
            conn: The connection to mark.
        """
        conn.is_healthy = False
        conn.error_count += 1

    def health_check(self) -> int:
        """Run a health check on all pooled connections.

        Removes connections that have exceeded error thresholds.

        Returns:
            Number of unhealthy connections removed.
        """
        removed = 0
        for server_id in list(self._connections.keys()):
            healthy = []
            for conn in self._connections[server_id]:
                if conn.error_count >= 3 or (conn.is_idle and not conn.is_healthy):
                    self._total_count -= 1
                    removed += 1
                else:
                    healthy.append(conn)
            if healthy:
                self._connections[server_id] = healthy
            else:
                del self._connections[server_id]
        return removed

    def _recycle_idle(self) -> None:
        """Recycle idle connections to free up capacity."""
        for server_id in list(self._connections.keys()):
            for conn in list(self._connections[server_id]):
                if conn.is_idle:
                    self._connections[server_id].remove(conn)
                    self._total_count -= 1
                    logger.debug("recycled idle connection", server_id=server_id)

    @property
    def total_count(self) -> int:
        """Total number of connections in the pool."""
        return self._total_count

    @property
    def server_count(self) -> int:
        """Number of servers with active connections."""
        return len(self._connections)

    def get_stats(self) -> dict[str, Any]:
        """Return pool statistics.

        Returns:
            Dict with connection counts by server.
        """
        server_stats = {}
        for server_id, conns in self._connections.items():
            server_stats[server_id] = {
                "active": len(conns),
                "healthy": sum(1 for c in conns if c.is_healthy),
            }
        return {
            "total_connections": self._total_count,
            "servers": server_stats,
            "max_total": self._config.max_total_connections,
        }


# ---------------------------------------------------------------------------
# -- Auto-reconnect with exponential backoff --------------------------------
# ---------------------------------------------------------------------------


@dataclass
class ReconnectPolicy:
    """Configuration for auto-reconnect with exponential backoff.

    Attributes:
        base_delay_s: Initial delay before first reconnect attempt.
        max_delay_s: Maximum delay between attempts.
        jitter_factor: Random jitter factor applied to delay.
        max_retries: Maximum number of reconnect attempts (0 = infinite).
        backoff_multiplier: Exponential backoff multiplier.
    """

    base_delay_s: float = 1.0
    max_delay_s: float = 60.0
    jitter_factor: float = 0.1
    max_retries: int = 10
    backoff_multiplier: float = 2.0


def compute_backoff_delay(
    attempt: int,
    policy: ReconnectPolicy = ReconnectPolicy(),
) -> float:
    """Compute the delay before the next reconnect attempt.

    Uses exponential backoff with jitter:
        delay = min(base * multiplier^attempt, max_delay)
        delay = delay * (1 + random * jitter_factor)

    Args:
        attempt: Current retry attempt number (0-indexed).
        policy: Reconnect policy configuration.

    Returns:
        Delay in seconds.
    """
    delay = policy.base_delay_s * (policy.backoff_multiplier ** attempt)
    delay = min(delay, policy.max_delay_s)
    jitter = 1.0 + random.uniform(-policy.jitter_factor, policy.jitter_factor)
    return delay * jitter


# ---------------------------------------------------------------------------
# -- Streamable HTTP Transport ----------------------------------------------
# ---------------------------------------------------------------------------


@dataclass
class StreamableHTTPTransport:
    """SSE-based streaming MCP transport with auto-reconnect and pooling.

    This transport provides a streaming interface for MCP tool execution
    with real-time progress updates via Server-Sent Events.

    Usage::

        transport = StreamableHTTPTransport()
        events = []

        async for event in transport.stream_tool_execution(
            server_id="search-srv",
            tool_name="web_search",
            params={"query": "MCP protocol"},
        ):
            events.append(event)
            if event.event_type == SSEEventType.TOOL_COMPLETE:
                print("Tool finished!")

        # Auto-reconnect is handled automatically inside
        # stream_tool_execution.
    """

    pool: ConnectionPool = field(default_factory=ConnectionPool)
    reconnect_policy: ReconnectPolicy = field(default_factory=ReconnectPolicy)
    _event_callbacks: list[Callable[[SSEEvent], None]] = field(default_factory=list)
    _server_urls: dict[str, str] = field(default_factory=dict)

    def register_server(self, server_id: str, url: str) -> None:
        """Register an MCP server URL for routing.

        Args:
            server_id: Unique server identifier.
            url: Server base URL.
        """
        self._server_urls[server_id] = url
        logger.info("server registered", server_id=server_id, url=url)

    def unregister_server(self, server_id: str) -> None:
        """Remove a server registration.

        Args:
            server_id: Server identifier to remove.
        """
        self._server_urls.pop(server_id, None)

    def on_event(self, callback: Callable[[SSEEvent], None]) -> None:
        """Register a callback for streaming events.

        Args:
            callback: Function ``(SSEEvent) -> None`` called for every
                event in the stream.
        """
        self._event_callbacks.append(callback)

    def remove_event_callback(self, callback: Callable[[SSEEvent], None]) -> None:
        """Remove a previously registered event callback.

        Args:
            callback: The callback to remove.
        """
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    def generate_event(
        self,
        event_type: SSEEventType,
        data: dict[str, Any] | None = None,
        server_id: str = "",
    ) -> SSEEvent:
        """Create and emit an SSE event.

        All registered callbacks receive the event.

        Args:
            event_type: The event type.
            data: Optional event payload.
            server_id: Optional server identifier.

        Returns:
            The generated ``SSEEvent``.
        """
        event = SSEEvent(
            event_type=event_type,
            data=data or {},
            server_id=server_id,
        )
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.warning("event callback failed", error=str(e))
        return event

    async def stream_tool_execution(
        self,
        server_id: str,
        tool_name: str,
        params: dict[str, Any] | None = None,
    ) -> list[SSEEvent]:
        """Stream a tool execution with real-time progress events.

        This is the main streaming interface. It:
        1. Acquires a connection from the pool.
        2. Sends the tool invocation.
        3. Streams back SSE progress events.
        4. Automatically reconnects on connection failure.
        5. Returns all collected events.

        **Stub implementation** — real deployments replace the
        ``_simulate_stream`` with actual HTTP SSE consumption.

        Args:
            server_id: Target MCP server.
            tool_name: Name of the tool to invoke.
            params: Tool parameters.

        Returns:
            List of all ``SSEEvent`` collected during the stream.
        """
        params = params or {}
        url = self._server_urls.get(server_id, "")

        if not url:
            error_event = self.generate_event(
                SSEEventType.TOOL_ERROR,
                {"error": f"Server '{server_id}' not registered", "tool": tool_name},
                server_id,
            )
            return [error_event]

        all_events: list[SSEEvent] = []
        attempt = 0

        while True:
            try:
                # Acquire connection
                conn = self.pool.acquire(server_id, url)

                # Emit start event
                start_event = self.generate_event(
                    SSEEventType.TOOL_START,
                    {"tool": tool_name, "params": params, "server": server_id},
                    server_id,
                )
                all_events.append(start_event)

                # Stream the execution (simulated or real)
                stream_events = await self._execute_stream(
                    conn, server_id, tool_name, params,
                )
                all_events.extend(stream_events)

                # Release connection on success
                self.pool.release(conn)
                break

            except (ConnectionError, TimeoutError, OSError) as e:
                logger.warning(
                    "stream connection failed",
                    server_id=server_id,
                    attempt=attempt,
                    error=str(e),
                )

                # Emit reconnect event
                reconnect_event = self.generate_event(
                    SSEEventType.CONNECTION_STATUS,
                    {"status": "reconnecting", "attempt": attempt, "error": str(e)},
                    server_id,
                )
                all_events.append(reconnect_event)

                # Check retry limit
                attempt += 1
                if (
                    self.reconnect_policy.max_retries > 0
                    and attempt > self.reconnect_policy.max_retries
                ):
                    error_event = self.generate_event(
                        SSEEventType.TOOL_ERROR,
                        {
                            "error": f"Max retries ({self.reconnect_policy.max_retries}) exceeded",
                            "tool": tool_name,
                        },
                        server_id,
                    )
                    all_events.append(error_event)
                    break

                # Wait with backoff
                delay = compute_backoff_delay(attempt - 1, self.reconnect_policy)
                logger.info("reconnecting", attempt=attempt, delay_s=round(delay, 2))
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(
                    "stream execution error",
                    server_id=server_id,
                    error=str(e),
                )
                error_event = self.generate_event(
                    SSEEventType.TOOL_ERROR,
                    {"error": str(e), "tool": tool_name},
                    server_id,
                )
                all_events.append(error_event)
                break

        return all_events

    async def _execute_stream(
        self,
        conn: Connection,
        server_id: str,
        tool_name: str,
        params: dict[str, Any],
    ) -> list[SSEEvent]:
        """Execute a tool and stream back SSE events.

        **Stub implementation.** In production this would perform:
            1. Open an HTTP connection to ``url/stream``.
            2. Send tool invocation as initial POST body.
            3. Read SSE events from the response body stream.
            4. Yield each parsed event.

        This stub simulates a sequence of SSE events for testing.
        """
        _ = conn  # unused in stub

        events: list[SSEEvent] = []
        n_steps = params.get("_simulated_steps", 3)

        for i in range(n_steps):
            progress = (i + 1) / n_steps
            event = self.generate_event(
                SSEEventType.TOOL_PROGRESS,
                {
                    "tool": tool_name,
                    "progress": progress,
                    "step": i + 1,
                    "total_steps": n_steps,
                },
                server_id,
            )
            events.append(event)

            # Simulate async execution delay
            await asyncio.sleep(0.01)

        # Heartbeat
        heartbeat = self.generate_event(
            SSEEventType.HEARTBEAT,
            {"server": server_id},
            server_id,
        )
        events.append(heartbeat)

        # Complete
        complete = self.generate_event(
            SSEEventType.TOOL_COMPLETE,
            {
                "tool": tool_name,
                "result": f"Completed {tool_name} with {len(params)} params",
                "execution_time_s": round(time.time() - events[0].timestamp, 3)
                if events else 0.0,
            },
            server_id,
        )
        events.append(complete)

        return events

    @property
    def registered_servers(self) -> list[str]:
        """List of registered server IDs."""
        return list(self._server_urls.keys())


__all__ = [
    "SSEEventType",
    "SSEEvent",
    "Connection",
    "ConnectionPool",
    "PoolConfig",
    "ReconnectPolicy",
    "StreamableHTTPTransport",
    "compute_backoff_delay",
]
