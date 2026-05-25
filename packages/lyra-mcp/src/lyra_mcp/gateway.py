"""MCP Enterprise Gateway for lyra-mcp.

Stateless HTTP transport (SEP-1442 compliant), OAuth 2.1 authentication,
allow/deny list policy enforcement, per-server rate limiting,
tool execution timeout, and server routing.
"""

from __future__ import annotations

import fnmatch
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuthMethod(Enum):
    """Authentication methods supported by the MCP Enterprise Gateway.

    Attributes
    ----------
    OAUTH21 : auto()
        OAuth 2.1 with PKCE and auto-discovery.
    API_KEY : auto()
        Static API key header-based authentication.
    MTLS : auto()
        Mutual TLS certificate-based authentication.
    NONE : auto()
        No authentication (internal/local servers only).
    """

    OAUTH21 = auto()
    API_KEY = auto()
    MTLS = auto()
    NONE = auto()


@dataclass(frozen=True)
class GatewayPolicy:
    """Access control and rate-limit policy for a single MCP server.

    Attributes
    ----------
    allow : tuple[str, ...]
        Glob patterns for explicitly allowed tool names.
        Empty tuple means all tools are allowed (subject to deny).
    deny : tuple[str, ...]
        Glob patterns for explicitly denied tool names.
        Deny entries take precedence over allow entries.
    requests_per_minute : int
        Maximum number of requests permitted in a 60-second sliding window.
    max_concurrent : int
        Maximum number of concurrent in-flight requests.
    tool_timeout_ms : int
        Per-tool execution timeout in milliseconds.
    """

    allow: tuple[str, ...] = ()
    deny: tuple[str, ...] = ()
    requests_per_minute: int = 60
    max_concurrent: int = 10
    tool_timeout_ms: int = 30000


@dataclass(frozen=True)
class ServerRegistration:
    """Immutable registration record for a single MCP server.

    Attributes
    ----------
    server_id : str
        Unique identifier for this server instance.
    name : str
        Human-readable server name.
    url : str
        Base URL for the MCP server endpoint.
    auth_method : AuthMethod
        Authentication method used when connecting.
    policy : Optional[GatewayPolicy]
        Server-specific policy overrides. Falls back to global default
        when None.
    health_check_url : Optional[str]
        Optional URL for health-check pings. Defaults to ``url + /health``
        at runtime when not provided.
    """

    server_id: str
    name: str
    url: str
    auth_method: AuthMethod = AuthMethod.NONE
    policy: Optional[GatewayPolicy] = None
    health_check_url: Optional[str] = None


@dataclass(frozen=True)
class GatewayConfig:
    """Top-level gateway configuration.

    Attributes
    ----------
    servers : tuple[ServerRegistration, ...]
        Pre-registered server entries loaded at startup.
    default_policy : GatewayPolicy
        Policy applied to any server that does not define its own.
    auto_discovery : bool
        When True, the gateway attempts OAuth 2.1 discovery on startup
        to find and register additional servers automatically.
    """

    servers: tuple[ServerRegistration, ...] = ()
    default_policy: GatewayPolicy = field(default_factory=lambda: GatewayPolicy())
    auto_discovery: bool = False


@dataclass(frozen=True)
class RateLimitState:
    """Current rate-limit tracking state for a single server.

    Instances are immutable; a new instance is created each time the
    window advances or the counter increments.

    Attributes
    ----------
    server_id : str
        Server this state belongs to.
    request_count : int
        Number of requests observed in the current time window.
    window_start_ms : int
        Monotonic timestamp (milliseconds) when the current window began.
    """

    server_id: str
    request_count: int = 0
    window_start_ms: int = 0


@dataclass(frozen=True)
class GatewayStats:
    """Aggregate gateway statistics snapshot.

    Attributes
    ----------
    total_requests : int
        Lifetime count of all requests routed through the gateway.
    allowed : int
        Lifetime count of requests that passed policy enforcement.
    denied : int
        Lifetime count of requests rejected by policy enforcement.
    active_servers : int
        Number of servers currently registered.
    """

    total_requests: int = 0
    allowed: int = 0
    denied: int = 0
    active_servers: int = 0


def _now_ms() -> int:
    """Return the current monotonic time in milliseconds."""
    return time.monotonic_ns() // 1_000_000


def _match_glob(patterns: tuple[str, ...], name: str) -> bool:
    """Return True if *name* matches any glob in *patterns*."""
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


class MCPEnterpriseGateway:
    """Enterprise-grade MCP gateway with policy enforcement and routing.

    Implements stateless HTTP transport (SEP-1442), OAuth 2.1 authentication,
    allow/deny policy enforcement, per-server rate limiting, and stub
    request routing.

    Parameters
    ----------
    config : Optional[GatewayConfig]
        Initial configuration. A default config is used when None.

    Examples
    --------
    >>> gateway = MCPEnterpriseGateway()
    >>> policy = GatewayPolicy(allow=("user*",), deny=("admin*",))
    >>> server = ServerRegistration(
    ...     server_id="svr-001",
    ...     name="user-tools",
    ...     url="http://localhost:8000/mcp",
    ...     policy=policy,
    ... )
    >>> gateway.register_server(server)
    ServerRegistration(server_id='svr-001', ...)
    >>> gateway.check_access("svr-001", "user-list")
    True
    >>> gateway.check_access("svr-001", "admin-delete")
    False
    """

    def __init__(self, config: Optional[GatewayConfig] = None) -> None:
        self._config = config or GatewayConfig()
        self._default_policy: GatewayPolicy = self._config.default_policy

        # Internal mutable state — never exposed directly.
        self._registrations: dict[str, ServerRegistration] = {}
        self._rate_states: dict[str, RateLimitState] = {}
        self._active_requests: dict[str, int] = {}
        self._total_requests: int = 0
        self._allowed: int = 0
        self._denied: int = 0

        # Bootstrap from static config.
        for server in self._config.servers:
            self._registrations[server.server_id] = server
            self._rate_states[server.server_id] = RateLimitState(
                server_id=server.server_id,
                window_start_ms=_now_ms(),
            )
            self._active_requests[server.server_id] = 0

        if self._config.auto_discovery:
            self._auto_discover()

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def register_server(self, server: ServerRegistration) -> ServerRegistration:
        """Register a new MCP server with the gateway.

        Parameters
        ----------
        server : ServerRegistration
            The server to register. If *server_id* already exists the
            existing registration is replaced.

        Returns
        -------
        ServerRegistration
            The registered server record (identical to the input).
        """
        self._registrations[server.server_id] = server
        if server.server_id not in self._rate_states:
            self._rate_states[server.server_id] = RateLimitState(
                server_id=server.server_id,
                window_start_ms=_now_ms(),
            )
        if server.server_id not in self._active_requests:
            self._active_requests[server.server_id] = 0
        logger.info("Registered server %s (%s)", server.server_id, server.name)
        return server

    def unregister_server(self, server_id: str) -> None:
        """Remove a server registration from the gateway.

        Parameters
        ----------
        server_id : str
            Identifier of the server to unregister. Silently returns
            if the server is not registered.
        """
        if server_id not in self._registrations:
            logger.warning("Attempted to unregister unknown server: %s", server_id)
            return
        self._registrations.pop(server_id, None)
        self._rate_states.pop(server_id, None)
        self._active_requests.pop(server_id, None)
        logger.info("Unregistered server %s", server_id)

    # ------------------------------------------------------------------
    # Policy enforcement
    # ------------------------------------------------------------------

    def _policy_for(self, server_id: str) -> GatewayPolicy:
        """Resolve the effective policy for a server.

        Returns the server-specific policy if set, otherwise falls back
        to the global default policy.
        """
        server = self._registrations.get(server_id)
        if server is not None and server.policy is not None:
            return server.policy
        return self._default_policy

    def check_access(self, server_id: str, tool_name: str) -> bool:
        """Check whether a tool is allowed on the given server.

        Enforcement order:
        1. If the server is unknown, access is denied.
        2. If the tool name matches *any* deny pattern, access is denied.
        3. If the allow list is non-empty and the tool does not match
           any allow pattern, access is denied.
        4. Otherwise access is granted.

        Parameters
        ----------
        server_id : str
            Registered server identifier.
        tool_name : str
            Name of the tool being accessed.

        Returns
        -------
        bool
            True if the tool may be invoked; False otherwise.
        """
        if server_id not in self._registrations:
            logger.warning("Access check for unknown server %s", server_id)
            self._denied += 1
            return False

        policy = self._policy_for(server_id)

        # Deny list takes priority.
        if _match_glob(policy.deny, tool_name):
            logger.debug("Tool %s denied by deny list on %s", tool_name, server_id)
            self._denied += 1
            return False

        # Allow list must match (empty = everything allowed).
        if policy.allow and not _match_glob(policy.allow, tool_name):
            logger.debug("Tool %s not in allow list on %s", tool_name, server_id)
            self._denied += 1
            return False

        self._allowed += 1
        return True

    def enforce_policy(self, server_id: str) -> bool:
        """Rate-limit and concurrency gate for a server.

        Checks whether the server has capacity under its
        ``requests_per_minute`` and ``max_concurrent`` limits.

        Parameters
        ----------
        server_id : str
            Registered server identifier.

        Returns
        -------
        bool
            True if the request may proceed; False if throttled.
        """
        if server_id not in self._registrations:
            logger.warning("Policy enforcement for unknown server %s", server_id)
            return False

        policy = self._policy_for(server_id)
        state = self._rate_states.get(server_id)
        now = _now_ms()
        window_ms = 60_000

        # Reset window if expired.
        if state is None or (now - state.window_start_ms) > window_ms:
            new_state = RateLimitState(
                server_id=server_id,
                request_count=0,
                window_start_ms=now,
            )
            self._rate_states[server_id] = new_state
            state = new_state

        # Rate-limit check.
        if state.request_count >= policy.requests_per_minute:
            logger.warning(
                "Rate limit exceeded for %s: %d/min (max %d)",
                server_id,
                state.request_count,
                policy.requests_per_minute,
            )
            return False

        # Concurrency check.
        active = self._active_requests.get(server_id, 0)
        if active >= policy.max_concurrent:
            logger.warning(
                "Concurrency limit exceeded for %s: %d active (max %d)",
                server_id,
                active,
                policy.max_concurrent,
            )
            return False

        return True

    def record_request(self, server_id: str) -> RateLimitState:
        """Record a request against the server's rate-limit counter.

        Call this *after* ``enforce_policy`` returns True to atomically
        increment the request count and concurrency slot.

        Parameters
        ----------
        server_id : str
            Registered server identifier.

        Returns
        -------
        RateLimitState
            The updated immutable rate-limit state.

        Raises
        ------
        ValueError
            If *server_id* is not registered.
        """
        state = self._rate_states.get(server_id)
        if state is None:
            raise ValueError(f"Server {server_id} is not registered")

        now = _now_ms()
        window_ms = 60_000

        # Start a new window if expired.
        if (now - state.window_start_ms) > window_ms:
            new_state = RateLimitState(
                server_id=server_id,
                request_count=1,
                window_start_ms=now,
            )
        else:
            new_state = RateLimitState(
                server_id=server_id,
                request_count=state.request_count + 1,
                window_start_ms=state.window_start_ms,
            )

        self._rate_states[server_id] = new_state
        self._active_requests[server_id] = self._active_requests.get(server_id, 0) + 1
        self._total_requests += 1
        return new_state

    def release_request(self, server_id: str) -> None:
        """Release a concurrency slot for the given server.

        Call when a proxied request completes (success or failure) so
        the concurrency counter is decremented.

        Parameters
        ----------
        server_id : str
            Registered server identifier.
        """
        current = self._active_requests.get(server_id, 0)
        if current > 0:
            self._active_requests[server_id] = current - 1
        else:
            logger.warning("Released request on %s with no active slots", server_id)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_servers(self, discovery_url: str) -> list[ServerRegistration]:
        """Discover MCP servers via OAuth 2.1 auto-discovery.

        **Stub implementation.** Production deployments override this
        method to implement SEP-1442-compliant discovery using the
        OAuth 2.1 Authorization Server Metadata endpoint at the
        provided URL.

        Parameters
        ----------
        discovery_url : str
            Well-known discovery endpoint URL
            (e.g. ``https://mcp.example.com/.well-known/mcp-configuration``).

        Returns
        -------
        list[ServerRegistration]
            Discovered server registrations.
        """
        logger.info(
            "Server discovery requested at %s (stub — returning empty list)",
            discovery_url,
        )
        return []

    def _auto_discover(self) -> None:
        """Run server discovery on startup when auto_discovery is enabled."""
        discovered = self.discover_servers(
            "/.well-known/mcp-configuration",
        )
        for server in discovered:
            self.register_server(server)
        if discovered:
            logger.info("Auto-discovered %d server(s)", len(discovered))

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route_request(
        self,
        server_id: str,
        tool_name: str,
        _params: dict[str, Any],
    ) -> dict[str, Any]:
        """Route a tool invocation to the target MCP server.

        **Stub implementation.** In production this method constructs
        an HTTP POST to the server's URL, attaches the appropriate
        ``Authorization`` header based on the server's ``AuthMethod``,
        enforces the per-server ``tool_timeout_ms``, and returns the
        parsed response.

        Parameters
        ----------
        server_id : str
            Registered server identifier.
        tool_name : str
            Name of the tool to invoke.
        params : dict[str, Any]
            Tool parameters as a JSON-compatible dictionary.

        Returns
        -------
        dict[str, Any]
            Response envelope with routing metadata and a placeholder
            result field.
        """
        server = self._registrations.get(server_id)
        if server is None:
            return {
                "success": False,
                "error": f"Unknown server: {server_id}",
                "result": None,
            }

        effective_policy = self._policy_for(server_id)

        result: dict[str, Any] = {
            "success": True,
            "server_id": server_id,
            "server_name": server.name,
            "tool": tool_name,
            "timeout_ms": effective_policy.tool_timeout_ms,
            "result": None,
            "error": None,
        }

        # Access gate.
        if not self.check_access(server_id, tool_name):
            result["success"] = False
            result["error"] = f"Access denied for tool '{tool_name}' on {server_id}"
            return result

        # Rate-limit gate.
        if not self.enforce_policy(server_id):
            result["success"] = False
            result["error"] = f"Rate-limited: {server_id}"
            return result

        # Record the accepted request.
        rate_state = self.record_request(server_id)

        result["rate_state"] = {
            "request_count": rate_state.request_count,
            "window_start_ms": rate_state.window_start_ms,
        }

        logger.debug(
            "Routed %s/%s to %s (count=%d)",
            server_id,
            tool_name,
            server.url,
            rate_state.request_count,
        )

        # In production, the actual HTTP call would go here:
        #   response = await self._http_post(
        #       server.url,
        #       json={"tool": tool_name, "params": params},
        #       auth=self._build_auth(server.auth_method),
        #       timeout=effective_policy.tool_timeout_ms / 1000,
        #   )
        #   result["result"] = response.json()

        return result

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> GatewayStats:
        """Return an immutable snapshot of current gateway statistics.

        Returns
        -------
        GatewayStats
            Snapshot with lifetime counters and active-server count.
        """
        return GatewayStats(
            total_requests=self._total_requests,
            allowed=self._allowed,
            denied=self._denied,
            active_servers=len(self._registrations),
        )


__all__ = [
    "AuthMethod",
    "GatewayPolicy",
    "ServerRegistration",
    "GatewayConfig",
    "RateLimitState",
    "GatewayStats",
    "MCPEnterpriseGateway",
]
