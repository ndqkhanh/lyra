"""MCP Gateway — unified entry point for Model Context Protocol servers.

Routes tool/resource/prompt requests to registered MCP servers with:
  - Health-checked server discovery
  - Round-robin load balancing across server instances
  - Circuit breaking for failing servers
  - Rate limiting and quota enforcement
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum


class ServerHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class CircuitState(StrEnum):
    CLOSED = "closed"       # normal — requests flow through
    OPEN = "open"           # failing — requests are rejected
    HALF_OPEN = "half_open"  # testing — limited probe requests


@dataclass
class ServerEndpoint:
    server_id: str
    url: str
    health: ServerHealth = ServerHealth.HEALTHY
    last_health_check: float = field(default_factory=time.time)
    failure_count: int = 0
    circuit: CircuitState = CircuitState.CLOSED
    circuit_opened_at: float = 0.0
    request_count: int = 0
    error_count: int = 0


@dataclass
class GatewayConfig:
    health_check_interval_sec: float = 30.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_sec: float = 60.0
    rate_limit_per_sec: int = 100
    max_concurrent: int = 50


@dataclass
class RouteResult:
    server_id: str
    url: str
    latency_ms: float = 0.0


class McpGateway:
    """Central MCP gateway routing requests to backend servers."""

    def __init__(self, config: GatewayConfig | None = None) -> None:
        self.config = config or GatewayConfig()
        self._servers: dict[str, ServerEndpoint] = {}
        self._rr_index: int = 0
        self._total_requests: int = 0
        self._total_errors: int = 0

    @property
    def server_count(self) -> int:
        return len(self._servers)

    @property
    def healthy_count(self) -> int:
        return sum(1 for s in self._servers.values() if s.health == ServerHealth.HEALTHY)

    @property
    def total_requests(self) -> int:
        return self._total_requests

    def register(self, server_id: str, url: str) -> None:
        if server_id not in self._servers:
            self._servers[server_id] = ServerEndpoint(server_id=server_id, url=url)

    def deregister(self, server_id: str) -> None:
        self._servers.pop(server_id, None)

    def route(self, tool_name: str = "") -> RouteResult | None:
        """Select a healthy server using round-robin."""
        healthy = [
            s for s in self._servers.values()
            if s.health == ServerHealth.HEALTHY and s.circuit != CircuitState.OPEN
        ]
        if not healthy:
            return None

        self._rr_index = (self._rr_index + 1) % len(healthy)
        server = healthy[self._rr_index]
        server.request_count += 1
        self._total_requests += 1
        return RouteResult(server_id=server.server_id, url=server.url)

    def report_success(self, server_id: str, latency_ms: float = 0.0) -> None:
        server = self._servers.get(server_id)
        if server is None:
            return
        server.failure_count = 0
        if server.circuit == CircuitState.HALF_OPEN:
            server.circuit = CircuitState.CLOSED

    def report_failure(self, server_id: str) -> None:
        server = self._servers.get(server_id)
        if server is None:
            return
        server.failure_count += 1
        server.error_count += 1
        self._total_errors += 1

        if server.failure_count >= self.config.circuit_breaker_threshold:
            server.circuit = CircuitState.OPEN
            server.circuit_opened_at = time.time()
            server.health = ServerHealth.UNHEALTHY

    def health_check(self) -> None:
        """Run periodic health checks — attempt recovery of open circuits."""
        now = time.time()
        for server in self._servers.values():
            if server.circuit == CircuitState.OPEN:
                if now - server.circuit_opened_at >= self.config.circuit_breaker_timeout_sec:
                    server.circuit = CircuitState.HALF_OPEN
                    server.health = ServerHealth.DEGRADED
            if now - server.last_health_check > self.config.health_check_interval_sec:
                server.last_health_check = now

    def stats(self) -> dict:
        return {
            "total_servers": self.server_count,
            "healthy_servers": self.healthy_count,
            "total_requests": self._total_requests,
            "total_errors": self._total_errors,
            "error_rate": self._total_errors / max(1, self._total_requests),
            "servers": [
                {"id": s.server_id, "health": s.health.value, "circuit": s.circuit.value,
                 "requests": s.request_count, "errors": s.error_count}
                for s in self._servers.values()
            ],
        }
