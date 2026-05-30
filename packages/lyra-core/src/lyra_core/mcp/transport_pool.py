"""Transport Pool — Connection pooling and lifecycle for MCP server transports.

Manages a bounded pool of connections to MCP servers with automatic
reconnection, health tracking, and retry with exponential backoff.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import StrEnum


class TransportType(StrEnum):
    """Transport protocol types for MCP servers."""

    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"


class ConnectionState(StrEnum):
    """Lifecycle states of a pooled connection."""

    IDLE = "idle"
    CONNECTING = "connecting"
    ACTIVE = "active"
    DRAINING = "draining"
    CLOSED = "closed"
    ERROR = "error"


class PoolStatus(StrEnum):
    """Overall pool health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    EXHAUSTED = "exhausted"
    SHUTDOWN = "shutdown"


@dataclass(frozen=True)
class TransportConfig:
    """Configuration for a transport connection."""

    transport_type: TransportType
    command: str = ""          # For stdio: the binary to spawn
    args: tuple[str, ...] = () # For stdio: CLI arguments
    url: str = ""              # For HTTP/SSE/WS: endpoint URL
    headers: tuple[tuple[str, str], ...] = ()  # For HTTP: extra headers
    connect_timeout: float = 10.0
    idle_timeout: float = 300.0
    max_retries: int = 3


@dataclass(frozen=True)
class ConnectionInfo:
    """Metadata about a single connection in the pool."""

    connection_id: str
    server_name: str
    transport_type: TransportType
    state: ConnectionState
    created_at: float
    last_used_at: float
    retry_count: int = 0
    error_message: str = ""


@dataclass
class PoolStats:
    """Current statistics for a transport pool."""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    error_connections: int = 0
    waiting_requests: int = 0
    status: PoolStatus = PoolStatus.HEALTHY
    avg_wait_ms: float = 0.0
    uptime_seconds: float = 0.0


class TransportPool:
    """Bounded connection pool for MCP server transports.

    Manages connections with automatic reconnection, health tracking,
    and retry with exponential backoff.

    Usage::

        pool = TransportPool(max_connections_per_server=3, max_total=20)
        pool.add_server("github", TransportConfig(
            transport_type=TransportType.HTTP,
            url="http://localhost:8080",
        ))
        conn = pool.acquire("github")
        # ... use connection ...
        pool.release(conn)
    """

    def __init__(
        self,
        max_connections_per_server: int = 5,
        max_total: int = 50,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 60.0,
        retry_backoff: float = 2.0,
        connection_ttl: float = 600.0,
    ) -> None:
        self.max_connections_per_server = max_connections_per_server
        self.max_total = max_total
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay
        self.retry_backoff = retry_backoff
        self.connection_ttl = connection_ttl

        self._servers: dict[str, TransportConfig] = {}
        self._connections: dict[str, ConnectionInfo] = {}
        self._waiting: dict[str, list[str]] = {}  # server_name -> [conn_id]
        self._lock = threading.Lock()
        self._started_at: float | None = None
        self._next_conn_id = 0

    # ── Server Management ──────────────────────────────────────────

    def add_server(self, name: str, config: TransportConfig) -> None:
        """Register a server with the pool."""
        with self._lock:
            self._servers[name] = config
            if name not in self._waiting:
                self._waiting[name] = []

    def remove_server(self, name: str) -> int:
        """Remove a server and close all its connections. Returns count closed."""
        with self._lock:
            self._servers.pop(name, None)
            closed = 0
            for conn_id, info in list(self._connections.items()):
                if info.server_name == name:
                    self._connections[conn_id] = ConnectionInfo(
                        connection_id=conn_id,
                        server_name=name,
                        transport_type=info.transport_type,
                        state=ConnectionState.CLOSED,
                        created_at=info.created_at,
                        last_used_at=time.monotonic(),
                    )
                    closed += 1
            self._waiting.pop(name, None)
            return closed

    def get_server_config(self, name: str) -> TransportConfig | None:
        """Get the transport config for a registered server."""
        return self._servers.get(name)

    def list_servers(self) -> list[str]:
        """List all registered server names."""
        return list(self._servers.keys())

    # ── Connection Lifecycle ───────────────────────────────────────

    def acquire(self, server_name: str) -> ConnectionInfo | None:
        """Acquire a connection from the pool.

        Returns a ConnectionInfo if a connection is available, or None
        if the pool is exhausted.
        """
        with self._lock:
            if self._started_at is None:
                self._started_at = time.monotonic()

            config = self._servers.get(server_name)
            if config is None:
                return None

            # Check for available idle connection to this server
            for conn_id, info in list(self._connections.items()):
                if (
                    info.server_name == server_name
                    and info.state == ConnectionState.IDLE
                ):
                    updated = ConnectionInfo(
                        connection_id=conn_id,
                        server_name=server_name,
                        transport_type=info.transport_type,
                        state=ConnectionState.ACTIVE,
                        created_at=info.created_at,
                        last_used_at=time.monotonic(),
                    )
                    self._connections[conn_id] = updated
                    return updated

            # Check if we can create a new connection
            server_count = sum(
                1 for i in self._connections.values()
                if i.server_name == server_name
                and i.state in (ConnectionState.IDLE, ConnectionState.ACTIVE, ConnectionState.CONNECTING)
            )

            total_count = sum(
                1 for i in self._connections.values()
                if i.state in (ConnectionState.IDLE, ConnectionState.ACTIVE, ConnectionState.CONNECTING)
            )

            if server_count >= self.max_connections_per_server:
                return None  # Server pool exhausted

            if total_count >= self.max_total:
                return None  # Total pool exhausted

            # Create new connection
            conn_id = self._generate_connection_id()
            info = ConnectionInfo(
                connection_id=conn_id,
                server_name=server_name,
                transport_type=config.transport_type,
                state=ConnectionState.CONNECTING,
                created_at=time.monotonic(),
                last_used_at=time.monotonic(),
            )
            self._connections[conn_id] = info
            return info

    def release(self, conn_id: str) -> bool:
        """Release a connection back to the pool."""
        with self._lock:
            info = self._connections.get(conn_id)
            if info is None:
                return False

            if info.state in (ConnectionState.CLOSED, ConnectionState.ERROR):
                return False

            updated = ConnectionInfo(
                connection_id=conn_id,
                server_name=info.server_name,
                transport_type=info.transport_type,
                state=ConnectionState.IDLE,
                created_at=info.created_at,
                last_used_at=time.monotonic(),
            )
            self._connections[conn_id] = updated
            return True

    def mark_error(self, conn_id: str, error_message: str = "") -> None:
        """Mark a connection as having errored."""
        with self._lock:
            info = self._connections.get(conn_id)
            if info is None:
                return
            self._connections[conn_id] = ConnectionInfo(
                connection_id=conn_id,
                server_name=info.server_name,
                transport_type=info.transport_type,
                state=ConnectionState.ERROR,
                created_at=info.created_at,
                last_used_at=time.monotonic(),
                retry_count=info.retry_count + 1,
                error_message=error_message,
            )

    def close_connection(self, conn_id: str) -> bool:
        """Permanently close a connection."""
        with self._lock:
            info = self._connections.get(conn_id)
            if info is None:
                return False
            self._connections[conn_id] = ConnectionInfo(
                connection_id=conn_id,
                server_name=info.server_name,
                transport_type=info.transport_type,
                state=ConnectionState.CLOSED,
                created_at=info.created_at,
                last_used_at=time.monotonic(),
                retry_count=info.retry_count,
                error_message=info.error_message,
            )
            return True

    # ── Retry Logic ────────────────────────────────────────────────

    def should_retry(self, conn_id: str) -> bool:
        """Check if a connection should be retried."""
        with self._lock:
            info = self._connections.get(conn_id)
            if info is None:
                return False

            config = self._servers.get(info.server_name)
            if config is None:
                return False

            return info.retry_count < config.max_retries

    def retry_delay(self, conn_id: str) -> float:
        """Calculate the retry delay with exponential backoff and jitter."""
        with self._lock:
            info = self._connections.get(conn_id)
            if info is None:
                return 0.0

            import random
            delay = self.retry_base_delay * (self.retry_backoff ** info.retry_count)
            delay = min(delay, self.retry_max_delay)
            jitter = random.uniform(0, delay * 0.1)
            return delay + jitter

    def retry_connection(self, conn_id: str) -> ConnectionInfo | None:
        """Retry a failed connection. Returns None if max retries exceeded."""
        with self._lock:
            info = self._connections.get(conn_id)
            if info is None:
                return None

            if not self.should_retry(conn_id):
                return None

            updated = ConnectionInfo(
                connection_id=conn_id,
                server_name=info.server_name,
                transport_type=info.transport_type,
                state=ConnectionState.CONNECTING,
                created_at=info.created_at,
                last_used_at=time.monotonic(),
                retry_count=info.retry_count + 1,
            )
            self._connections[conn_id] = updated
            return updated

    # ── Connection Info ────────────────────────────────────────────

    def get_connection(self, conn_id: str) -> ConnectionInfo | None:
        """Get info for a specific connection."""
        return self._connections.get(conn_id)

    def get_server_connections(self, server_name: str) -> list[ConnectionInfo]:
        """Get all connections for a server."""
        return [
            info for info in self._connections.values()
            if info.server_name == server_name
        ]

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> PoolStats:
        """Get current pool statistics."""
        with self._lock:
            active = sum(
                1 for i in self._connections.values()
                if i.state in (ConnectionState.ACTIVE, ConnectionState.CONNECTING)
            )
            idle_count = sum(
                1 for i in self._connections.values()
                if i.state == ConnectionState.IDLE
            )
            error_count = sum(
                1 for i in self._connections.values()
                if i.state == ConnectionState.ERROR
            )
            total = len(self._connections)
            waiting = sum(len(w) for w in self._waiting.values())
            uptime = (
                time.monotonic() - self._started_at
                if self._started_at else 0.0
            )

            # Determine pool status
            if self._started_at is None:
                status = PoolStatus.SHUTDOWN
            elif total >= self.max_total:
                status = PoolStatus.EXHAUSTED
            elif error_count > 0 and active + idle_count == 0:
                status = PoolStatus.DEGRADED
            else:
                status = PoolStatus.HEALTHY

            return PoolStats(
                total_connections=total,
                active_connections=active,
                idle_connections=idle_count,
                error_connections=error_count,
                waiting_requests=waiting,
                status=status,
                uptime_seconds=uptime,
            )

    def reap_idle_connections(self) -> int:
        """Close connections that have been idle beyond the TTL. Returns count."""
        now = time.monotonic()
        reaped = 0
        with self._lock:
            for conn_id, info in list(self._connections.items()):
                if info.state == ConnectionState.IDLE:
                    idle_duration = now - info.last_used_at
                    if idle_duration > self.connection_ttl:
                        self._connections[conn_id] = ConnectionInfo(
                            connection_id=conn_id,
                            server_name=info.server_name,
                            transport_type=info.transport_type,
                            state=ConnectionState.CLOSED,
                            created_at=info.created_at,
                            last_used_at=now,
                        )
                        reaped += 1
        return reaped

    def shutdown(self) -> int:
        """Shutdown the pool, closing all connections. Returns count."""
        with self._lock:
            count = 0
            for conn_id, info in list(self._connections.items()):
                self._connections[conn_id] = ConnectionInfo(
                    connection_id=conn_id,
                    server_name=info.server_name,
                    transport_type=info.transport_type,
                    state=ConnectionState.CLOSED,
                    created_at=info.created_at,
                    last_used_at=time.monotonic(),
                )
                count += 1
            self._servers.clear()
            self._waiting.clear()
            self._started_at = None
            return count

    def clear(self) -> None:
        """Clear all pool state (for testing)."""
        with self._lock:
            self._servers.clear()
            self._connections.clear()
            self._waiting.clear()
            self._started_at = None
            self._next_conn_id = 0

    # ── Private ────────────────────────────────────────────────────

    def _generate_connection_id(self) -> str:
        """Generate a unique connection ID."""
        self._next_conn_id += 1
        return f"conn-{self._next_conn_id:06d}"
